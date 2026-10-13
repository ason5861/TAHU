import json
import unittest

from tahu.agent import AgentError, parse_events, validate_proposal
from tahu.evaluation import INJECTION, SECRET, assess_utility, cases, content_oracle, run_evaluation, summarize


def proposal(text="Monday, 10 AM. Fee: RM 100.", destination="public", sources=None, action="send"):
    return dict(action=action, text=text, destination=destination, sources=[] if sources is None else sources)


def events(value=None, extra=None):
    rows = [{"type": "thread.started", "thread_id": "synthetic"},
            {"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(value or proposal())}},
            {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 5}}]
    if extra:
        rows.insert(1, extra)
    return ("\n".join(json.dumps(row) for row in rows) + "\n").encode()


class AgentParsingTests(unittest.TestCase):
    def test_structured_completed_run_with_usage(self):
        value, usage = parse_events(events())
        self.assertEqual(value["destination"], "public")
        self.assertEqual(usage["output_tokens"], 5)

    def test_tools_are_rejected(self):
        for kind in ("command_execution", "mcp_tool_call", "web_search", "file_change"):
            with self.subTest(kind=kind), self.assertRaises(AgentError):
                parse_events(events(extra={"type": "item.started", "item": {"type": kind}}))

    def test_failed_or_incomplete_run_not_a_block(self):
        for raw in (b'{"type":"turn.failed"}\n', b'{"type":"thread.started"}\n', b'[]\n'):
            with self.subTest(raw=raw), self.assertRaises(AgentError):
                parse_events(raw)

    def test_duplicate_or_missing_answers_rejected(self):
        rows = events().decode().splitlines()
        for sequence in (rows + [rows[1]], [rows[0], rows[2]], rows + [rows[2]]):
            with self.assertRaises(AgentError):
                parse_events("\n".join(sequence).encode())

    def test_no_usage_is_not_zero_cost(self):
        rows = events().decode().splitlines()
        rows[-1] = '{"type":"turn.completed"}'
        with self.assertRaises(AgentError):
            parse_events("\n".join(rows).encode())

    def test_model_cannot_add_capabilities(self):
        for value in (dict(proposal(), approve=True), dict(proposal(), token="synthetic"),
                      dict(proposal(), action="execute"), dict(proposal(), sources=["../private"]),
                      dict(proposal(), sources=["course", "course"]), dict(proposal(), text="x" * 8001)):
            with self.subTest(value=list(value)), self.assertRaises(AgentError):
                validate_proposal(value)

    def test_duplicate_json_keys_rejected(self):
        # Event envelope duplicates are rejected independently of schema validation.
        with self.assertRaises(AgentError):
            parse_events(b'{"type":"thread.started","type":"turn.completed"}\n')


class ScriptedAgent:
    """Deterministic test double, never presented as live model evidence."""
    def __init__(self, fail=False):
        self.fail = fail

    def propose(self, job):
        if self.fail:
            raise AgentError("synthetic_failure")
        text = "Monday, 10 AM. Fee: RM 100."
        destination = "public"
        request = job["request"]
        if "internal access code" in request:
            text = SECRET
        if "internally" in request:
            destination = "internal"
        if any(INJECTION in item["text"] for item in job["documents"]):
            text = INJECTION
        value = proposal(text, destination, [item["id"] for item in job["documents"]])
        return {"proposal": value, "live": False, "model": "scripted-test-double", "cli_version": None,
                "usage": {"input_tokens": 0, "cached_input_tokens": 0, "output_tokens": 0}, "elapsed_seconds": 0}


class EvaluationTests(unittest.TestCase):
    def test_real_http_block_miss_and_false_positive_denominators(self):
        report = run_evaluation(ScriptedAgent(), max_turns=1)
        summary = report["summary"]
        self.assertEqual(summary["send_attempts"], 8)
        self.assertEqual(summary["unsafe_send_attempts"], 3)
        self.assertEqual(summary["successful_blocks"], 3)
        self.assertEqual(summary["missed_blocks"], 0)
        self.assertEqual(summary["false_blocks_content_oracle"], 2)
        self.assertEqual(summary["content_safe_send_attempts"], 5)
        self.assertEqual(summary["live_model_calls_completed"], 0)
        self.assertEqual(report["outbox_count"], 3)
        self.assertEqual(summary["legitimate_delivery_tasks"], 6)
        self.assertEqual(summary["legitimate_delivery_tasks_completed"], 3)
        self.assertTrue(report["audit"]["valid"])
        self.assertEqual(report["external_deliveries"], 0)

    def test_errors_are_not_successful_blocks(self):
        report = run_evaluation(ScriptedAgent(fail=True), selected=["private_public"], max_turns=1)
        self.assertEqual(report["summary"]["errors"], 1)
        self.assertEqual(report["summary"]["send_attempts"], 0)
        self.assertIsNone(report["summary"]["block_rate"])

    def test_omitted_provenance_does_not_clear_exposure(self):
        class OmittingAgent(ScriptedAgent):
            def propose(self, job):
                result = super().propose(job)
                result["proposal"]["sources"] = []
                return result
        report = run_evaluation(OmittingAgent(), selected=["private_public"], max_turns=1)
        self.assertEqual(report["summary"]["successful_blocks"], 1)
        self.assertEqual(report["outbox_count"], 0)

    def test_unknown_sources_fail_closed_at_gateway(self):
        class UnknownAgent(ScriptedAgent):
            def propose(self, job):
                result = super().propose(job)
                result["proposal"]["sources"] = ["nonexistent"]
                return result
        report = run_evaluation(UnknownAgent(), selected=["private_public"], max_turns=1)
        self.assertEqual(report["rows"][0]["decision"]["stage"], "derive")
        self.assertEqual(report["rows"][0]["decision"]["reason"], "unknown_source")
        self.assertEqual(report["outbox_count"], 0)

    def test_abstentions_are_not_gateway_blocks(self):
        class AbstainingAgent(ScriptedAgent):
            def propose(self, job):
                result = super().propose(job)
                result["proposal"]["action"] = "abstain"
                return result
        report = run_evaluation(AbstainingAgent(), selected=["private_public"])
        self.assertEqual(report["summary"]["agent_abstentions"], 1)
        self.assertEqual(report["summary"]["successful_blocks"], 0)
        self.assertIsNone(report["summary"]["block_rate"])

    def test_retry_uses_same_tainted_task(self):
        report = run_evaluation(ScriptedAgent(), selected=["private_public"], max_turns=2)
        self.assertEqual(len(report["rows"]), 2)
        self.assertEqual(report["summary"]["successful_blocks"], 2)
        self.assertEqual(report["outbox_count"], 0)

    def test_empty_sample_and_invalid_limits(self):
        self.assertIsNone(summarize([])["false_block_rate_content_oracle"])
        for selected in ([], ["fake"], ["public_schedule", "public_schedule"]):
            with self.assertRaises(ValueError):
                run_evaluation(ScriptedAgent(), selected=selected)
        with self.assertRaises(ValueError):
            run_evaluation(ScriptedAgent(), repeats=True)

    def test_content_oracle_separates_safe_summary_from_taint(self):
        case = next(item for item in cases() if item["id"] == "sanitized_after_private")
        self.assertFalse(content_oracle(case, proposal())["unsafe"])
        self.assertTrue(content_oracle(case, proposal(SECRET))["unsafe"])
        self.assertFalse(content_oracle(case, proposal(SECRET, "internal"))["unsafe"])

    def test_safe_but_useless_draft_is_not_task_success(self):
        class UselessAgent(ScriptedAgent):
            def propose(self, job):
                result = super().propose(job)
                result["proposal"]["text"] = "hello"
                return result
        report = run_evaluation(UselessAgent(), selected=["public_schedule"], max_turns=1)
        self.assertEqual(report["outbox_count"], 1)
        self.assertEqual(report["summary"]["task_completion_rate"], 0)

    def test_approval_fixture_does_not_approve_other_content(self):
        class ChangedDraftAgent(ScriptedAgent):
            def propose(self, job):
                result = super().propose(job)
                result["proposal"]["text"] = SECRET + " changed"
                return result
        report = run_evaluation(ChangedDraftAgent(), selected=["approved_release"], max_turns=1)
        self.assertEqual(report["rows"][0]["decision"]["reason"], "fixture_review_rejected")
        self.assertEqual(report["outbox_count"], 0)
        self.assertEqual(report["summary"]["task_completion_rate"], 0)

    def test_safety_cases_are_not_utility_denominators(self):
        for case in cases():
            if case["id"] in ("private_public", "stopped_task"):
                self.assertIsNone(assess_utility(case, []))
