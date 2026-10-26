"""Trusted local integration fixture; no OS isolation of the Python host."""
import secrets
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path

from .client import Client
from .core import Gateway
from .localmail import local_mailbox
from .server import make_server


@contextmanager
def mail_gateway():
    """Separate unguarded comparison sink and guarded TAHU execution sink."""
    with tempfile.TemporaryDirectory(prefix="tahu_mail_boundary_") as directory:
        gateway = Gateway(Path(directory) / "state.sqlite3")
        with local_mailbox() as baseline, local_mailbox(guarded=True, receipt_path=Path(directory) / "receiver.sqlite3") as guarded:
            operator_token = secrets.token_urlsafe(48)
            server = make_server(gateway, operator_token, 0, mail_executor=guarded._execute, mail_receipts=guarded.receipt)
            thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
            thread.start()
            url = "http://127.0.0.1:" + str(server.server_port)
            try:
                yield Client(url, operator_token), url, baseline, guarded
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=3)
