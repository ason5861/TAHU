"""No CLI, credentials, or network required for these boundary regressions."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tahu.agent import AgentError, CodexAgent, copy_cli_auth, proposal_environment


class StartupTests(unittest.TestCase):
    def agent(self):
        agent = CodexAgent.__new__(CodexAgent)
        agent.executable, agent.model, agent.timeout, agent.version = "codex", "test", 10, "test"
        return agent

    def test_environment_excludes_parent_context_and_provider_credentials(self):
        parent = {"PATH": "os-path", "SystemRoot": "os-root", "CODEX_HOME": "old-profile",
                  "HOME": "old-home", "USERPROFILE": "old-user", "OPENAI_API_KEY": "fake-key",
                  "CODEX_THREAD_ID": "old-thread", "OPENAI_BASE_URL": "https://invalid.example",
                  "CODEX_CONTEXT": "extra", "UNRELATED_SECRET": "fake-secret"}
        with patch.dict(os.environ, parent, clear=True):
            env = proposal_environment(Path("profile"), Path("user"))
        self.assertEqual(env["PATH"], "os-path")
        self.assertEqual({key.upper(): value for key, value in env.items()}["SYSTEMROOT"], "os-root")
        for key in ("OPENAI_API_KEY", "CODEX_THREAD_ID", "OPENAI_BASE_URL", "CODEX_CONTEXT", "UNRELATED_SECRET"):
            self.assertNotIn(key, env)
        self.assertEqual(env["CODEX_HOME"], "profile")
        self.assertEqual(env["USERPROFILE"], "user")

    def test_copies_only_auth_and_missing_auth_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            source, target = Path(root) / "source", Path(root) / "target"
            source.mkdir(); target.mkdir()
            (source / "auth.json").write_text('{"synthetic":"not-a-credential"}')
            (source / "AGENTS.md").write_text("private instructions must not copy")
            (source / "config.toml").write_text('developer_instructions="extra"')
            with patch.dict(os.environ, {"CODEX_HOME": str(source)}):
                copy_cli_auth(target)
                self.assertEqual([p.name for p in target.iterdir()], ["auth.json"])
                self.assertEqual((target / "auth.json").read_bytes(), (source / "auth.json").read_bytes())
                (source / "auth.json").unlink()
                with self.assertRaisesRegex(AgentError, "^isolated_cli_file_auth_unavailable$"):
                    copy_cli_auth(target)

    def test_proposal_separates_credentials_work_home_and_cleans_failure(self):
        paths = []
        def auth(profile):
            (profile / "auth.json").write_text('{"synthetic":"not-a-credential"}')
        def run(command, payload, timeout, **kwargs):
            env = kwargs["env"]
            profile, home = Path(env["CODEX_HOME"]), Path(env["HOME"])
            work = Path(command[command.index("--cd") + 1])
            paths.extend([profile, home, work])
            self.assertEqual(len({profile, home, work}), 3)
            self.assertNotIn(profile, work.parents)
            self.assertFalse((work / "auth.json").exists())
            self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
            self.assertIn("--ignore-user-config", command)
            for feature in ("shell_tool", "multi_agent", "apps", "plugins", "hooks", "browser_use", "computer_use", "image_generation"):
                self.assertIn(["--disable", feature], [command[i:i+2] for i in range(len(command)-1)])
            self.assertNotIn(b"not-a-credential", payload)
            raise RuntimeError("worker_failed")
        with patch("tahu.agent.copy_cli_auth", auth), patch("tahu.agent._bounded_process", run):
            with self.assertRaisesRegex(AgentError, "^live_agent_run_failed$"):
                self.agent().propose({"documents": []})
        self.assertTrue(paths)
        self.assertTrue(all(not path.exists() for path in paths))

    def test_success_reports_configuration_not_runtime_attestation(self):
        answer = {"action": "abstain", "text": "", "sources": [], "destination": "public"}
        raw = (json.dumps({"type": "item.completed", "item": {"type": "agent_message", "text": json.dumps(answer)}})
               + '\n' + json.dumps({"type": "turn.completed", "usage": {"input_tokens": 1, "cached_input_tokens": 0, "output_tokens": 1}})).encode()
        with patch("tahu.agent.copy_cli_auth"), patch("tahu.agent._bounded_process", return_value=raw):
            result = self.agent().propose({"documents": []})
        self.assertFalse(result["startup"]["runtime_context_attested"])

