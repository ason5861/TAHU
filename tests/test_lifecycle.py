import unittest
from unittest.mock import patch

from scripts.evaluate_lifecycle import ARMS, run
from tests.test_mail import SyntheticMailAgent
from tahu.agent import AgentError, CodexAgent


class LifecycleTests(unittest.TestCase):
    def test_independent_inputs_recovery_and_no_duplicate_effects(self):
        providers = {arm: SyntheticMailAgent() for arm in ARMS}
        report = run(providers)
        self.assertEqual(len(report["rows"]), 18)
        self.assertTrue(all(len(provider.jobs) == 6 for provider in providers.values()))
        for case in {row["case"] for row in report["rows"]}:
            self.assertEqual(len({row["job_sha256"] for row in report["rows"] if row["case"] == case}), 1)
        self.assertEqual(report["summary"]["unmediated"]["unauthorized_effects"], 3)
        self.assertEqual(report["summary"]["tahu"]["unauthorized_effects"], 0)
        self.assertEqual(report["summary"]["tahu"]["unsafe_proposals_blocked_by_gateway"], 3)
        self.assertEqual(report["summary"]["tahu"]["reconciled_deliveries"], 2)
        for row in report["rows"]:
            if row.get("initial_execution"):
                self.assertEqual(row["initial_execution"]["status"], "UNKNOWN")
                self.assertEqual(row["replay_execution"]["status"], "SUCCEEDED")
                self.assertEqual(row["receiver_count"], 1)
        self.assertTrue(report["audit"]["valid"])

    def test_failed_model_calls_remain_in_original_denominator(self):
        report = run({arm: SyntheticMailAgent(fail=True) for arm in ARMS})
        for value in report["summary"].values():
            self.assertEqual(value["tasks"], 6)
            self.assertEqual(value["errors"], 6)
            self.assertEqual(value["legitimate_tasks"], 4)
            self.assertEqual(value["legitimate_completed"], 0)
            self.assertEqual(value["unsafe_proposals_blocked_by_gateway"], 0)

    def test_neutral_prompt_baseline_retains_native_tool_restrictions(self):
        agent = object.__new__(CodexAgent)
        agent.model, agent.timeout, agent.executable, agent.version = "synthetic", 1, "native-codex", "fixture"
        agent.prompt_safeguards = False
        def capture(command, payload, timeout, **kwargs):
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            for feature in ("shell_tool", "apps", "plugins", "browser_use", "computer_use"):
                self.assertIn(["--disable", feature], [command[i:i+2] for i in range(len(command)-1)])
            self.assertNotIn(b"Do not disclose restricted", payload)
            raise RuntimeError("capture complete")
        with patch("tahu.agent.copy_cli_auth"), patch("tahu.agent._bounded_process", capture):
            with self.assertRaises(AgentError):
                agent.propose({"documents": []})
