import smtplib
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from tahu.core import Gateway
from tahu.localmail import local_mailbox
from tests.test_gateway import policy


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.g = Gateway(Path(self.temp.name) / "state.sqlite3")
        self.g.create_task(policy())
        self.mail = local_mailbox(guarded=True)
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
