"""Small SMTP test sink. Loopback only, .test recipients, never a mail relay.

This is experiment infrastructure, not a production SMTP implementation.
"""
import smtplib
import hmac
import secrets
import sqlite3
import socketserver
import threading
from contextlib import contextmanager
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import SMTP
from pathlib import Path

from .core import digest


RECIPIENTS = {"public": "parent@example.test", "internal": "staff@example.test"}
SENDER = "agent@example.test"


@contextmanager
def _receiver_db(path):
    db = sqlite3.connect(path, timeout=3)
    try:
        with db:
            yield db
    finally:
        db.close()


def _message(body, destination, message_id, payload_hash=None):
    message = EmailMessage(policy=SMTP)
    message["From"] = SENDER
    message["To"] = RECIPIENTS[destination]
    message["Subject"] = "Synthetic robotics course reply"
    message["Message-ID"] = "<" + message_id + "@example.test>"
    if payload_hash is not None:
        message["X-TAHU-Payload-Digest"] = payload_hash
    message.set_content(body)
    return message


class _Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.connection.settimeout(3)
        sender, recipient = None, None
        authenticated = self.server.executor_secret is None

        def reply(text):
            self.wfile.write((text + "\r\n").encode("ascii"))
            self.wfile.flush()

        reply("220 localhost TAHU synthetic test sink")
        for _ in range(30):
            try:
                line = self.rfile.readline(4097)
                if not line or len(line) > 4096:
                    return
                command = line.decode("ascii").strip()
                upper = command.upper()
                if upper.startswith(("EHLO ", "HELO ")):
                    reply("250 localhost")
                elif upper == "QUIT":
                    reply("221 goodbye")
                    return
                elif upper == "RSET":
                    sender, recipient = None, None
                    reply("250 reset")
                elif upper == "NOOP":
                    reply("250 ok")
                elif upper.startswith("XTAHU "):
                    authenticated = bool(self.server.executor_secret and hmac.compare_digest(command[6:], self.server.executor_secret))
                    reply("250 executor accepted" if authenticated else "550 executor required")
                elif not authenticated:
                    reply("550 executor authentication required")
                elif upper == "MAIL FROM:<" + SENDER.upper() + ">":
                    sender, recipient = SENDER, None
                    reply("250 sender accepted")
                elif upper.startswith("MAIL FROM:"):
                    reply("550 synthetic sender required")
                elif upper.startswith("RCPT TO:"):
                    address = command[8:].strip().strip("<>").lower()
                    if sender and address in RECIPIENTS.values() and recipient is None:
                        recipient = address
                        reply("250 recipient accepted")
                    else:
                        reply("550 allowlisted single .test recipient required")
                elif upper == "DATA" and sender and recipient:
                    reply("354 end with dot")
                    body = bytearray()
                    while True:
                        block = self.rfile.readline(8193)
                        if not block or len(block) > 8192:
                            return
                        if block == b".\r\n":
                            break
                        if block.startswith(b".."):
                            block = block[1:]
                        body.extend(block)
                        if len(body) > 65536:
                            reply("552 message limit")
                            return
                    accepted = self.server.capture(sender, recipient, bytes(body))
                    sender, recipient = None, None
                    reply("250 captured locally" if accepted else "550 conflicting or invalid execution ID")
                else:
                    reply("502 unsupported command or sequence")
            except (OSError, UnicodeError):
                return


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False


class MailSink:
    def __init__(self, guarded=False, receipt_path=None):
        if receipt_path is not None and not guarded:
            raise ValueError("durable_receipts_require_guarded_sink")
        self.receipt_path = str(Path(receipt_path).resolve()) if receipt_path is not None else None
        if self.receipt_path:
            with _receiver_db(self.receipt_path) as db:
                db.execute("PRAGMA synchronous=FULL")
                db.execute("CREATE TABLE IF NOT EXISTS received (id TEXT PRIMARY KEY, sender TEXT NOT NULL, recipient TEXT NOT NULL, data BLOB NOT NULL)")
        self.server = _Server(("127.0.0.1", 0), _Handler)
        self.server.messages = []
        # Fixture-only capability. Keep it in the trusted host, out of model
        # inputs. Python object privacy is not an OS security boundary.
        self.server.executor_secret = secrets.token_urlsafe(48) if guarded else None
        self.server.lock = threading.Lock()
        self.server.capture = self._capture
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def messages(self):
        if self.receipt_path:
            with _receiver_db(self.receipt_path) as db:
                return [{"sender": row[0], "recipient": row[1], "data": row[2]}
                        for row in db.execute("SELECT sender,recipient,data FROM received ORDER BY rowid")]
        with self.server.lock:
            return list(self.server.messages)

    def _capture(self, sender, recipient, raw):
        if not self.receipt_path:
            with self.server.lock:
                self.server.messages.append({"sender": sender, "recipient": recipient, "data": raw})
            return True
        parsed = BytesParser(policy=SMTP).parsebytes(raw)
        ids = parsed.get_all("Message-ID", [])
        if len(ids) != 1:
            return False
        delivery_id = str(ids[0]).removeprefix("<").removesuffix("@example.test>")
        if len(delivery_id) != 32 or any(c not in "0123456789abcdef" for c in delivery_id):
            return False
        if str(ids[0]) != "<" + delivery_id + "@example.test>":
            return False
        with _receiver_db(self.receipt_path) as db:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT sender,recipient,data FROM received WHERE id=?", (delivery_id,)).fetchone()
            if old:
                return old == (sender, recipient, raw)
            db.execute("INSERT INTO received VALUES(?,?,?,?)", (delivery_id, sender, recipient, raw))
        # The durable receiver record is the fixture's side effect. A repeated
        # identical execution ID acknowledges this record without inserting twice.
        return True

    def receipt(self, entry):
        """Trusted host lookup; never expose receiver data to task credentials."""
        if not self.receipt_path:
            raise ValueError("durable_receiver_required")
        with _receiver_db(self.receipt_path) as db:
            row = db.execute("SELECT recipient,data FROM received WHERE id=?", (entry["id"],)).fetchone()
        if row is None:
            return None
        payload = {"task": entry["task"], "op": "send", "artifact": entry["artifact"],
                   "destination": entry["destination"], "text": entry["text"]}
        expected = _message(entry["text"], entry["destination"], entry["id"], digest(payload)).as_bytes()
        matches = row[0] == RECIPIENTS[entry["destination"]] and row[1] == expected
        return {"delivery_id": entry["id"], "payload_hash": digest(payload) if matches else None}

    def send(self, body, destination, message_id):
        if self.server.executor_secret is not None:
            raise ValueError("guarded_sink_requires_gateway_execution")
        return self._send(body, destination, message_id)

    def _execute(self, entry):
        if self.server.executor_secret is None:
            raise ValueError("guarded_sink_required")
        payload = {"task": entry["task"], "op": "send", "artifact": entry["artifact"],
                   "destination": entry["destination"], "text": entry["text"]}
        return self._send(entry["text"], entry["destination"], entry["id"], self.server.executor_secret, digest(payload))

    def _send(self, body, destination, message_id, executor_secret=None, payload_hash=None):
        if destination not in RECIPIENTS or not isinstance(body, str) or len(body) > 8000:
            raise ValueError("invalid_local_mail")
        # Only the body is model-controlled. Header/envelope fields are host-fixed.
        message = _message(body, destination, message_id, payload_hash)
        with smtplib.SMTP("127.0.0.1", self.server.server_address[1], timeout=3) as client:
            if executor_secret is not None:
                code, _ = client.docmd("XTAHU", executor_secret)
                if code != 250:
                    raise ValueError("local_executor_authentication_failed")
            client.send_message(message)
        return {"sink": "loopback_smtp", "recipient": RECIPIENTS[destination], "message_id": message_id}


@contextmanager
def local_mailbox(guarded=False, receipt_path=None):
    sink = MailSink(guarded=guarded, receipt_path=receipt_path)
    sink.thread.start()
    try:
        yield sink
    finally:
        sink.server.shutdown()
        sink.server.server_close()
        sink.thread.join(timeout=3)
