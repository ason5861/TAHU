import smtplib
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from tahu.core import Gateway
from tahu.localmail import local_mailbox
from tahu.localmail import MailSink
from tahu.mail_fixture import mail_gateway
from tahu.client import Client
from tests.test_gateway import policy


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.g = Gateway(Path(self.temp.name) / "state.sqlite3")
        self.g.create_task(policy())
        self.mail = local_mailbox(guarded=True, receipt_path=Path(self.temp.name) / "receiver.sqlite3")
        self.sink = self.mail.__enter__()

    def tearDown(self):
        self.mail.__exit__(None, None, None)
        self.temp.cleanup()

    def queue(self, artifact="public", destination="public", request="send"):
        response = self.g.step("research", {"request_id": request, "op": "send", "id": artifact, "destination": destination})
        self.assertTrue(response["allowed"])
        return response["result"]["delivery_id"]

    def execute(self, delivery):
        return self.g.execute_delivery(delivery, self.sink._execute)

    def test_direct_send_and_raw_smtp_cannot_bypass_guarded_receiver(self):
        with self.assertRaisesRegex(ValueError, "requires_gateway"):
            self.sink.send("SYNTHETIC SECRET", "public", "forged")
        with smtplib.SMTP("127.0.0.1", self.sink.server.server_address[1], timeout=3) as client:
            self.assertEqual(client.docmd("XTAHU", "forged")[0], 550)
            self.assertEqual(client.mail("agent@example.test")[0], 550)
        self.assertEqual(self.sink.messages, [])

    def test_stop_after_queue_prevents_smtp_and_restart_does_not_restore_permission(self):
        delivery = self.queue()
        self.g.stop("research")
        self.g = Gateway(self.g.path)
        self.assertEqual(self.execute(delivery)["status"], "DENIED")
        self.assertEqual(self.sink.messages, [])

    def test_concurrent_execution_and_replay_have_one_receiver_effect(self):
        delivery = self.queue()
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.execute(delivery), range(8)))
        self.assertTrue(any(result["status"] == "SUCCEEDED" for result in results))
        self.assertEqual(self.execute(delivery)["status"], "SUCCEEDED")
        self.assertEqual(len(self.sink.messages), 1)

    def test_content_destination_and_policy_changes_are_denied(self):
        for index, statement in enumerate(("UPDATE outbox SET text='changed' WHERE id=?",
                                           "UPDATE outbox SET destination='internal' WHERE id=?",
                                           "UPDATE tasks SET policy='{}' WHERE id=(SELECT task FROM outbox WHERE id=?)")):
            with self.subTest(statement=statement):
                # A database owner is outside the threat model; partial corruption
                # must nevertheless fail closed, not silently change the effect.
                self.g.create_task(policy("task" + str(index)))
                response = self.g.step("task" + str(index), {"request_id": "send", "op": "send", "id": "public", "destination": "public"})
                delivery = response["result"]["delivery_id"]
                with self.g.transaction() as db:
                    db.execute(statement, (delivery,))
                self.assertEqual(self.execute(delivery)["status"], "DENIED")
        self.assertEqual(self.sink.messages, [])

    def test_expired_approval_is_rechecked_at_execution(self):
        self.g.approve({"task": "research", "artifact": "private", "destination": "public", "ttl": 1})
        delivery = self.queue("private")
        import time
        with patch("tahu.core.time.time", return_value=time.time() + 2):
            self.assertEqual(self.execute(delivery)["reason"], "approval_expired")
        self.assertEqual(self.sink.messages, [])

    def test_task_expiry_and_new_sensitive_exposure_are_rechecked(self):
        delivery = self.queue()
        self.g.step("research", {"request_id": "read", "op": "read", "id": "private"})
        self.assertEqual(self.execute(delivery)["reason"], "execution_review_required")
        delivery = self.queue("private", "internal", "internal")
        with self.g.transaction() as db:
            db.execute("UPDATE tasks SET expires=0")
        self.assertEqual(self.execute(delivery)["reason"], "task_expired")
        self.assertEqual(self.sink.messages, [])

    def test_policy_version_and_missing_manifest_fail_closed(self):
        delivery = self.queue()
        with patch("tahu.core.POLICY_VERSION", "future-policy"):
            self.assertEqual(self.execute(delivery)["reason"], "authorization_binding_changed")
        delivery = self.queue(request="legacy")
        with self.g.transaction() as db:
            db.execute("DELETE FROM executions WHERE id=?", (delivery,))
        self.assertEqual(self.execute(delivery)["reason"], "missing_execution_authorization")
        self.assertEqual(self.sink.messages, [])

    def test_lost_ack_is_unknown_and_never_automatically_retried(self):
        delivery = self.queue()
        def lost_ack(entry):
            self.sink._execute(entry)
            raise OSError("synthetic secret must not appear in audit")
        self.assertEqual(self.g.execute_delivery(delivery, lost_ack)["status"], "UNKNOWN")
        self.assertEqual(self.execute(delivery)["status"], "UNKNOWN")
        self.assertEqual(len(self.sink.messages), 1)
        self.assertNotIn("synthetic secret", str(self.g.inspect("audit")))

    def test_crash_after_effect_leaves_durable_unknown_without_retry(self):
        delivery = self.queue()
        class SimulatedCrash(BaseException):
            pass
        def crash(entry):
            self.sink._execute(entry)
            raise SimulatedCrash()
        with self.assertRaises(SimulatedCrash):
            self.g.execute_delivery(delivery, crash)
        self.g = Gateway(self.g.path)
        self.assertEqual(self.execute(delivery)["status"], "UNKNOWN")
        self.assertEqual(len(self.sink.messages), 1)

    def test_audit_failure_before_callback_has_no_effect(self):
        delivery = self.queue()
        with patch.object(Gateway, "audit", side_effect=RuntimeError("synthetic audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.execute(delivery)
        self.assertEqual(self.sink.messages, [])

    def test_lost_ack_reconciles_after_gateway_and_receiver_restart(self):
        delivery = self.queue()
        def lost_ack(entry):
            self.sink._execute(entry)
            raise OSError("lost acknowledgement")
        self.assertEqual(self.g.execute_delivery(delivery, lost_ack)["status"], "UNKNOWN")
        self.mail.__exit__(None, None, None)
        self.mail = local_mailbox(guarded=True, receipt_path=Path(self.temp.name) / "receiver.sqlite3")
        self.sink = self.mail.__enter__()
        self.g = Gateway(self.g.path)
        self.g.stop("research")
        result = self.g.reconcile_delivery(delivery, self.sink.receipt)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(self.execute(delivery)["status"], "SUCCEEDED")
        self.assertEqual(len(self.sink.messages), 1)
        self.assertTrue(self.g.verify_audit()["valid"])

    def test_missing_or_wrong_receipt_cannot_authorize_retry(self):
        delivery = self.queue()
        with self.g.transaction() as db:
            db.execute("UPDATE executions SET status='EXECUTING' WHERE id=?", (delivery,))
        for lookup in (lambda entry: None,
                       lambda entry: {"delivery_id": "0" * 32, "payload_hash": "forged"},
                       lambda entry: {"delivery_id": delivery, "payload_hash": "forged"}):
            self.assertEqual(self.g.reconcile_delivery(delivery, lookup)["status"], "UNKNOWN")
            self.assertEqual(self.execute(delivery)["status"], "UNKNOWN")
        self.assertEqual(self.sink.messages, [])

    def test_receiver_idempotency_and_conflicting_payload(self):
        delivery = self.queue()
        entry = next(row for row in self.g.inspect("outbox") if row["id"] == delivery)
        self.sink._execute(entry)
        self.sink._execute(entry)
        with self.assertRaises(smtplib.SMTPDataError):
            self.sink._execute(dict(entry, text="substituted"))
        self.assertEqual(len(self.sink.messages), 1)
        # Exact receipt verification includes trailing newlines and MIME bytes.
        self.assertIsNotNone(self.sink.receipt(entry)["payload_hash"])
        self.assertIsNone(self.sink.receipt(dict(entry, text=entry["text"] + "\n"))["payload_hash"])

    def test_http_lifecycle_reconciles_unknown_without_another_effect(self):
        original = MailSink._execute
        def uncertain(sink, entry):
            original(sink, entry)
            raise OSError("lost SMTP acknowledgement")
        with patch.object(MailSink, "_execute", uncertain):
            with mail_gateway() as (operator, url, baseline, guarded):
                identity = operator.call("/v1/tasks", policy("http_trial"))
                task = Client(url, identity["token"])
                proposal = task.step({"request_id": "send", "op": "send", "id": "public", "destination": "public"})
                request = {"delivery_id": proposal["result"]["delivery_id"]}
                self.assertEqual(operator.call("/v1/execute-mail", request)["status"], "UNKNOWN")
                operator.call("/v1/stop", {"task": "http_trial"})
                self.assertEqual(operator.call("/v1/reconcile-mail", request)["status"], "SUCCEEDED")
                self.assertEqual(operator.call("/v1/execute-mail", request)["status"], "SUCCEEDED")
                self.assertEqual(len(guarded.messages), 1)

    def test_actual_executor_process_exit_after_capture_is_reconciled(self):
        delivery = self.queue()
        child = """
import json, os, smtplib, sys
from tahu.core import Gateway, digest
from tahu.localmail import _message
config = json.load(sys.stdin)
def crash_after_capture(entry):
    payload = {"task": entry["task"], "op": "send", "artifact": entry["artifact"],
               "destination": entry["destination"], "text": entry["text"]}
    with smtplib.SMTP("127.0.0.1", config["port"], timeout=3) as client:
        code, _ = client.docmd("XTAHU", config["capability"])
        if code != 250:
            raise RuntimeError("fixture authentication failed")
        client.send_message(_message(entry["text"], entry["destination"], entry["id"], digest(payload)))
    os._exit(23)
Gateway(config["state"]).execute_delivery(config["delivery"], crash_after_capture)
"""
        config = {"state": self.g.path, "delivery": delivery,
                  "port": self.sink.server.server_address[1], "capability": self.sink.server.executor_secret}
        result = subprocess.run([sys.executable, "-c", child], input=json.dumps(config),
                                capture_output=True, text=True, timeout=15,
                                cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode, 23, "synthetic executor did not reach crash point")
        self.g = Gateway(self.g.path)
        self.assertEqual(self.execute(delivery)["status"], "UNKNOWN")
        self.assertEqual(self.g.reconcile_delivery(delivery, self.sink.receipt)["status"], "SUCCEEDED")
        self.assertEqual(self.execute(delivery)["status"], "SUCCEEDED")
        self.assertEqual(len(self.sink.messages), 1)

    def test_stop_waits_for_inflight_effect_and_denies_later_execution(self):
        first = self.queue()
        second = self.queue(request="later")
        entered, release, stop_started = threading.Event(), threading.Event(), threading.Event()
        def bounded(entry):
            entered.set()
            if not release.wait(3):
                raise RuntimeError("test timeout")
            self.sink._execute(entry)
        def stop():
            stop_started.set()
            return self.g.stop("research")
        with ThreadPoolExecutor(max_workers=2) as pool:
            execution = pool.submit(self.g.execute_delivery, first, bounded)
            try:
                self.assertTrue(entered.wait(3))
                stopped = pool.submit(stop)
                self.assertTrue(stop_started.wait(3))
                self.assertFalse(stopped.done())
            finally:
                release.set()
            self.assertEqual(execution.result(timeout=5)["status"], "SUCCEEDED")
            self.assertTrue(stopped.result(timeout=5)["stopped"])
        self.assertEqual(self.execute(second)["status"], "DENIED")
        self.assertEqual(len(self.sink.messages), 1)
