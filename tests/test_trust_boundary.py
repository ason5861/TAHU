"""HTTP/guarded-SMTP evidence and explicit trusted-host counterexamples.

These are author-written deterministic proposals, not model or independent tests.
"""
import unittest
from urllib.error import HTTPError

from tahu.client import Client
from tahu.mail_fixture import mail_gateway
from tests.test_gateway import policy


class TrustBoundaryTests(unittest.TestCase):
    def test_transformed_and_split_outputs_keep_exposure_without_marker_matching(self):
        # No content detector is being tested: even harmless math is refused.
        variants = ("The access phrase is SYNTHETIC SECRET",
                    "U1lOVEhFVElDIFNFQ1JFVA==", "S Y N T H E T I C",
                    "S E C R E T", "The protected phrase starts with SYN.", "2 + 2 = 4")
        with mail_gateway() as (operator, url, baseline, guarded):
            identity = operator.call("/v1/tasks", policy())
            agent = Client(url, identity["token"])
            self.assertTrue(agent.step({"request_id": "read", "op": "read", "id": "private"})["allowed"])
            for index, text in enumerate(variants):
                with self.subTest(index=index):
                    derived = agent.step({"request_id": "derive" + str(index), "op": "derive",
                                          "id": "renamed" + str(index), "sources": ["public"], "text": text})
                    self.assertEqual(derived["result"]["labels"], ["restricted"])
                    decision = agent.step({"request_id": "send" + str(index), "op": "send",
                                           "id": "renamed" + str(index), "destination": "public"})
                    self.assertFalse(decision["allowed"])
                    self.assertEqual(decision["reason"], "information_flow_denied")
            self.assertEqual(operator.call("/v1/outbox", {})["items"], [])
            self.assertEqual(guarded.messages, [])
            self.assertEqual(baseline.messages, [])
            self.assertTrue(operator.call("/v1/audit/verify", {})["valid"])

    def test_agent_cannot_replace_labels_and_missing_initial_labels_are_rejected(self):
        with mail_gateway() as (operator, url, baseline, guarded):
            invalid = policy("missing")
            del invalid["artifacts"][1]["labels"]
            with self.assertRaises(HTTPError) as rejected:
                operator.call("/v1/tasks", invalid)
            self.assertEqual(rejected.exception.code, 400)
            rejected.exception.close()
            identity = operator.call("/v1/tasks", policy())
            agent = Client(url, identity["token"])
            for index, extra in enumerate(({"labels": []}, {"trusted": True}, {"classification": "public"})):
                decision = agent.step(dict(request_id="forge" + str(index), op="derive", id="draft",
                                           sources=["private"], text="public claim", **extra))
                self.assertFalse(decision["allowed"])
                self.assertEqual(decision["reason"], "invalid_request_fields")
            overwrite = agent.step({"request_id": "overwrite", "op": "derive", "id": "private",
                                    "sources": ["public"], "text": "replacement"})
            self.assertEqual(overwrite["reason"], "immutable_artifact")
            self.assertEqual(agent.step({"request_id": "read", "op": "read", "id": "private"})["result"]["labels"], ["restricted"])
            self.assertEqual(guarded.messages, [])

    def test_unknown_exposure_survives_empty_sources_and_blocks_both_destinations(self):
        with mail_gateway() as (operator, url, baseline, guarded):
            identity = operator.call("/v1/tasks", policy())
            agent = Client(url, identity["token"])
            agent.step({"request_id": "read", "op": "read", "id": "unknown"})
            agent.step({"request_id": "derive", "op": "derive", "id": "new_name", "sources": [], "text": "a summary"})
            for destination in ("public", "internal"):
                decision = agent.step({"request_id": destination, "op": "send", "id": "new_name", "destination": destination})
                self.assertEqual(decision["reason"], "classification_required")
            self.assertEqual(guarded.messages, [])

    def test_trusted_mislabel_and_context_carryover_are_explicit_counterexamples(self):
        # Deliberately broken trusted-host assumptions. Successful delivery is a
        # recorded limit, never a successful safety test or model leak finding.
        with mail_gateway() as (operator, url, baseline, guarded):
            original = operator.call("/v1/tasks", policy("original"))
            old_agent = Client(url, original["token"])
            carried = old_agent.step({"request_id": "read", "op": "read", "id": "private"})["result"]["text"]
            for task_id in ("wrong_label", "reused_context"):
                data = policy(task_id)
                data["artifacts"] = ([{"id": "input", "text": "SYNTHETIC SECRET", "labels": []}]
                                     if task_id == "wrong_label" else [])
                identity = operator.call("/v1/tasks", data)
                agent = Client(url, identity["token"])
                if task_id == "wrong_label":
                    agent.step({"request_id": "read", "op": "read", "id": "input"})
                else:
                    agent.step({"request_id": "derive", "op": "derive", "id": "input", "sources": [], "text": carried})
                decision = agent.step({"request_id": "send", "op": "send", "id": "input", "destination": "public"})
                self.assertTrue(decision["allowed"])
                receipt = operator.call("/v1/execute-mail", {"delivery_id": decision["result"]["delivery_id"]})
                self.assertEqual(receipt["status"], "SUCCEEDED")
            self.assertEqual(len(guarded.messages), 2)
            self.assertTrue(all(b"SYNTHETIC SECRET" in m["data"] for m in guarded.messages))
            self.assertEqual(baseline.messages, [])
