import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from tahu.core import Gateway, Invalid


def policy(name="research", budget=30, attempts=100):
    return {"id": name, "purpose": "Synthetic information-flow evaluation", "budget": budget,
            "attempt_limit": attempts, "ttl": 3600,
            "destinations": {"public": [], "internal": ["restricted"]},
            "artifacts": [{"id": "public", "text": "Public course information", "labels": []},
                          {"id": "private", "text": "SYNTHETIC SECRET", "labels": ["restricted"]},
                          {"id": "unknown", "text": "Unclassified", "labels": ["unknown"]}]}


class GatewayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "state.sqlite3"
        self.g = Gateway(self.path)
        self.identity = self.g.create_task(policy())
        self.counter = 0

    def tearDown(self):
        self.temp.cleanup()

    def step(self, op, id="public", task="research", **kwargs):
        self.counter += 1
        return self.g.step(task, dict(request_id=str(self.counter), op=op, id=id, **kwargs))

    def grant(self, id="private", destination="public", ttl=60):
        return self.g.approve({"task": "research", "artifact": id, "destination": destination, "ttl": ttl})

    def test_public_delivery_is_durable(self):
        self.assertTrue(self.step("send", destination="public")["allowed"])
        self.assertEqual(len(Gateway(self.path).inspect("outbox")), 1)

    def test_direct_private_leak_denied(self):
        self.assertEqual(self.step("send", "private", destination="public")["reason"], "information_flow_denied")
        self.assertEqual(self.g.inspect("outbox"), [])

    def test_internal_delivery_allowed(self):
        self.assertTrue(self.step("send", "private", destination="internal")["allowed"])

    def test_multihop_taint(self):
        self.step("derive", "first", sources=["private"], text="transformed")
        self.step("derive", "second", sources=["first"], text="transformed again")
        self.assertFalse(self.step("send", "second", destination="public")["allowed"])

    def test_omitted_provenance_denied(self):
        self.step("read", "private")
        self.step("derive", "leak", sources=[], text="SYNTHETIC SECRET")
        self.assertFalse(self.step("send", "leak", destination="public")["allowed"])

    def test_false_public_provenance_denied(self):
        self.step("read", "private")
        self.step("derive", "leak", sources=["public"], text="SYNTHETIC SECRET")
        self.assertFalse(self.step("send", "leak", destination="public")["allowed"])

    def test_existing_public_selection_after_secret_denied(self):
        self.step("read", "private")
        self.assertFalse(self.step("send", destination="public")["allowed"])

    def test_known_overblocking_is_not_hidden(self):
        self.step("read", "private")
        self.step("derive", "math", sources=[], text="2 + 2 = 4")
        self.assertFalse(self.step("send", "math", destination="public")["allowed"])

    def test_fresh_task_has_separate_registry_and_exposure(self):
        self.step("read", "private")
        clean = policy("clean")
        clean["artifacts"] = [clean["artifacts"][0]]
        self.g.create_task(clean)
        self.step("derive", "math", task="clean", sources=[], text="2 + 2 = 4")
        self.assertTrue(self.step("send", "math", task="clean", destination="public")["allowed"])
        self.assertFalse(self.step("read", "private", task="clean")["allowed"])

    def test_unknown_cannot_be_approved(self):
        self.assertFalse(self.step("send", "unknown", destination="internal")["allowed"])
        with self.assertRaises(Invalid):
            self.grant("unknown", "internal")

    def test_unknown_session_cannot_be_declassified(self):
        self.step("read", "unknown")
        with self.assertRaises(Invalid):
            self.grant("public")

    def test_one_use_grant(self):
        self.grant()
        self.assertTrue(self.step("send", "private", destination="public")["allowed"])
        self.assertFalse(self.step("send", "private", destination="public")["allowed"])

    def test_grant_bound_to_artifact(self):
        self.grant()
        self.step("derive", "copy", sources=["private"], text="SYNTHETIC SECRET")
        self.assertFalse(self.step("send", "copy", destination="public")["allowed"])

    def test_grant_bound_to_destination(self):
        self.grant(destination="internal")
        self.assertFalse(self.step("send", "private", destination="public")["allowed"])

    def test_expired_grant_denied(self):
        self.grant()
        with patch("tahu.core.time.time", return_value=10**12):
            # Extend task only to test approval expiry independently.
            with self.g.transaction() as db:
                db.execute("UPDATE tasks SET expires=?", (10**13,))
            self.assertFalse(self.step("send", "private", destination="public")["allowed"])

    def test_task_expiry(self):
        with patch("tahu.core.time.time", return_value=10**12):
            self.assertEqual(self.step("read")["reason"], "task_expired")

    def test_persistent_stop_overrides_grant_and_cached_read(self):
        request = {"request_id": "cached", "op": "read", "id": "public"}
        self.g.step("research", request)
        self.grant()
        self.g.stop("research")
        restarted = Gateway(self.path)
        self.assertEqual(restarted.step("research", request)["reason"], "task_stopped")
        self.assertFalse(self.step("send", "private", destination="public")["allowed"])

    def test_budget_and_attempt_limits(self):
        self.g.create_task(policy("limited", budget=1, attempts=2))
        self.assertTrue(self.step("read", task="limited")["allowed"])
        self.assertEqual(self.step("read", task="limited")["reason"], "action_budget")
        self.assertEqual(self.step("read", task="limited")["reason"], "attempt_limit")

    def test_rejections_consume_attempts(self):
        self.g.create_task(policy("limited", budget=1, attempts=1))
        self.step("bad", task="limited")
        self.assertEqual(self.step("read", task="limited")["reason"], "attempt_limit")

    def test_replay_does_not_duplicate_delivery(self):
        request = {"request_id": "retry", "op": "send", "id": "public", "destination": "public"}
        first = self.g.step("research", request)
        second = Gateway(self.path).step("research", request)
        self.assertEqual(first, second)
        self.assertEqual(len(self.g.inspect("outbox")), 1)

    def test_request_id_conflict(self):
        self.g.step("research", {"request_id": "same", "op": "read", "id": "public"})
        self.assertEqual(self.g.step("research", {"request_id": "same", "op": "read", "id": "private"})["reason"], "request_id_conflict")

    def test_malformed_inputs_are_denied_and_audited(self):
        for request in (None, [], 12, {"request_id": "bad1", "op": []}, {"request_id": "bad2", "op": {}}, {"request_id": "bad3", "op": "read", "id": []}):
            with self.subTest(request=request):
                before = len(self.g.inspect("audit"))
                self.assertFalse(self.g.step("research", request)["allowed"])
                self.assertEqual(len(self.g.inspect("audit")), before + 1)

    def test_labels_cannot_be_overridden(self):
        self.assertFalse(self.step("derive", "fake", sources=["private"], text="secret", labels=[])["allowed"])

    def test_artifact_cannot_be_overwritten(self):
        self.assertFalse(self.step("derive", sources=["private"], text="secret")["allowed"])

    def test_agent_cannot_change_policy_or_approve(self):
        for op in ("approve", "change_policy", "stop", "reset"):
            self.assertFalse(self.step(op)["allowed"])

    def test_input_mutation_does_not_change_audit(self):
        request = {"request_id": "mutable", "op": "derive", "id": "copy", "sources": ["private"], "text": "secret"}
        self.g.step("research", request)
        before = self.g.inspect("audit")
        request["sources"].clear()
        self.assertEqual(self.g.inspect("audit"), before)
        self.assertNotIn("SYNTHETIC SECRET", json.dumps(before))

    def test_audit_chain_and_tamper_detection(self):
        self.step("read")
        self.assertTrue(self.g.verify_audit()["valid"])
        with self.g.transaction() as db:
            db.execute("UPDATE audit SET event='{}' WHERE sequence=1")
        self.assertFalse(self.g.verify_audit()["valid"])

    def test_atomic_rollback_if_audit_fails(self):
        self.grant()
        with patch.object(Gateway, "audit", side_effect=sqlite3.OperationalError("simulated disk failure")):
            with self.assertRaises(sqlite3.OperationalError):
                self.step("send", "private", destination="public")
        self.assertEqual(self.g.inspect("outbox"), [])
        self.assertTrue(self.step("send", "private", destination="public")["allowed"])

    def test_concurrent_grant_use_allows_exactly_one_delivery(self):
        self.grant()
        def send(index):
            return self.g.step("research", {"request_id": "parallel_" + str(index), "op": "send", "id": "private", "destination": "public"})["allowed"]
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(send, range(8)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(len(self.g.inspect("outbox")), 1)

    def test_secrets_not_stored_as_tokens(self):
        self.assertEqual(self.g.authenticate(self.identity["token"]), "research")
        self.assertIsNone(self.g.authenticate("invalid"))
        self.assertNotIn(self.identity["token"].encode(), self.path.read_bytes())

    def test_task_policy_validation(self):
        for field, value in (("budget", True), ("destinations", {"public": ["unknown"]}), ("ttl", -1)):
            item = policy("invalid")
            item[field] = value
            with self.assertRaises(Invalid):
                self.g.create_task(item)
