"""Small SMTP test sink. Loopback only, .test recipients, never a mail relay.

This is experiment infrastructure, not a production SMTP implementation.
"""
import smtplib
import hmac
import secrets
import socketserver
import threading
from contextlib import contextmanager
from email.message import EmailMessage
from email.policy import SMTP


RECIPIENTS = {"public": "parent@example.test", "internal": "staff@example.test"}
SENDER = "agent@example.test"


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
                    with self.server.lock:
                        self.server.messages.append({"sender": sender, "recipient": recipient,
                                                     "data": bytes(body)})
                    sender, recipient = None, None
                    reply("250 captured locally")
                else:
                    reply("502 unsupported command or sequence")
            except (OSError, UnicodeError):
                return


class _Server(socketserver.ThreadingTCPServer):
    daemon_threads = True
    allow_reuse_address = False


class MailSink:
    def __init__(self, guarded=False):
        self.server = _Server(("127.0.0.1", 0), _Handler)
        self.server.messages = []
        # Fixture-only capability. Keep it in the trusted host, out of model
        # inputs. Python object privacy is not an OS security boundary.
        self.server.executor_secret = secrets.token_urlsafe(48) if guarded else None
        self.server.lock = threading.Lock()
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       kwargs={"poll_interval": 0.05}, daemon=True)

    @property
    def messages(self):
        with self.server.lock:
            return list(self.server.messages)

    def send(self, body, destination, message_id):
        if self.server.executor_secret is not None:
            raise ValueError("guarded_sink_requires_gateway_execution")
        return self._send(body, destination, message_id)

    def _execute(self, entry):
        if self.server.executor_secret is None:
            raise ValueError("guarded_sink_required")
        return self._send(entry["text"], entry["destination"], entry["id"], self.server.executor_secret)

    def _send(self, body, destination, message_id, executor_secret=None):
        if destination not in RECIPIENTS or not isinstance(body, str) or len(body) > 8000:
            raise ValueError("invalid_local_mail")
        # Only the body is model-controlled. Header/envelope fields are host-fixed.
        message = EmailMessage(policy=SMTP)
        message["From"] = SENDER
        message["To"] = RECIPIENTS[destination]
        message["Subject"] = "Synthetic robotics course reply"
        message["Message-ID"] = "<" + message_id + "@example.test>"
        message.set_content(body)
        with smtplib.SMTP("127.0.0.1", self.server.server_address[1], timeout=3) as client:
            if executor_secret is not None:
                code, _ = client.docmd("XTAHU", executor_secret)
                if code != 250:
                    raise ValueError("local_executor_authentication_failed")
            client.send_message(message)
        return {"sink": "loopback_smtp", "recipient": RECIPIENTS[destination], "message_id": message_id}


@contextmanager
def local_mailbox(guarded=False):
    sink = MailSink(guarded=guarded)
    sink.thread.start()
    try:
        yield sink
    finally:
        sink.server.shutdown()
        sink.server.server_close()
        sink.thread.join(timeout=3)
