"""Opt-in native CLI request capture; synthetic profiles, loopback, no model/auth.

The receiver deliberately returns HTTP 400. A captured request is evidence of
submitted context, not a successful model run or proof about all other hosts.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tahu.agent import CodexAgent, proposal_environment
from tahu.isolation import _bounded_process

MARKERS = {"global": "TAHU_GLOBAL_CANARY_71", "skill": "TAHU_SKILL_CANARY_82",
           "user_skill": "TAHU_USER_SKILL_CANARY_93", "config": "TAHU_CONFIG_CANARY_64"}


def probe(agent, hardened, override):
    captured = []
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            size = int(self.headers.get("Content-Length", "0"))
            if not 0 < size <= 1048576:
                self.send_error(413); return
            captured.append(json.loads(self.rfile.read(size)))
            self.send_response(400); self.end_headers()
            self.wfile.write(b'{"error":{"message":"synthetic capture complete"}}')
        def log_message(self, *args):
            pass
    with tempfile.TemporaryDirectory(prefix="tahu_canary_") as directory:
        root = Path(directory)
        profile, user = root / "profile", root / "user"
        profile.mkdir(); user.mkdir()
        (profile / "auth.json").write_text("{}", encoding="utf-8")
        (profile / ("AGENTS.override.md" if override else "AGENTS.md")).write_text(MARKERS["global"], encoding="utf-8")
        (profile / "config.toml").write_text('developer_instructions="' + MARKERS["config"] + '"', encoding="utf-8")
        for base, key in ((profile / "skills", "skill"), (user / ".agents" / "skills", "user_skill")):
            skill = base / ("synthetic-canary-" + key)
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_text('---\nname: synthetic-canary-' + key + '\ndescription: ' + MARKERS[key] + '\n---\nNo action.\n', encoding="utf-8")
        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def capture(command, payload, timeout, **kwargs):
            # Same adapter command, changing only transport to a no-auth local
            # receiver. Never pass real profile/auth or request headers to it.
            extra = ['model_provider="capture"', 'model_providers.capture.name="capture"',
                     f'model_providers.capture.base_url="http://127.0.0.1:{server.server_port}/v1"',
                     'model_providers.capture.requires_openai_auth=false',
                     'model_providers.capture.request_max_retries=0',
                     'model_providers.capture.stream_max_retries=0']
            command = command[:-1] + [part for setting in extra for part in ("-c", setting)] + ["-"]
            if not hardened:
                # Reconstruct the old inherited-profile launch, with the exact
                # same flags and safe synthetic parent instead of real context.
                kwargs["env"] = proposal_environment(profile, user)
            return _bounded_process(command, payload, timeout, **kwargs)
        try:
            with patch.dict(os.environ, proposal_environment(profile, user), clear=True), patch("tahu.agent._bounded_process", capture):
                try:
                    agent.propose({"request": "State the public course time.", "documents": [
                        {"id": "course", "text": "Course: Tuesday 10:00.", "labels": []}]})
                except RuntimeError:
                    pass  # The receiver intentionally rejects the request.
        finally:
            server.shutdown(); server.server_close(); thread.join(timeout=2)
        if len(captured) != 1:
            raise RuntimeError("expected_one_captured_request")
        request = captured[0]
        text = json.dumps(request)
        return {"mode": "isolated_profile" if hardened else "legacy_inherited_profile",
                "global_fixture": "AGENTS.override.md" if override else "AGENTS.md",
                "markers_in_submitted_request": {key: value in text for key, value in MARKERS.items()},
                "tool_names": [tool.get("name", tool.get("type")) for tool in request.get("tools", [])],
                "request_bytes": len(text.encode()), "receiver_status": 400}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true", help="explicitly run installed native Codex against loopback")
    parser.add_argument("--output", default="reports/startup-context.json")
    args = parser.parse_args()
    if not args.capture:
        parser.error("--capture required; this launches installed Codex, without model calls")
    agent = CodexAgent("gpt-6.1-sol", 45)
    rows = [probe(agent, hardened, override) for override in (False, True) for hardened in (False, True)]
    success = all(not any(row["markers_in_submitted_request"].values()) and not row["tool_names"]
                  if row["mode"] == "isolated_profile" else
                  row["markers_in_submitted_request"]["global"] and row["markers_in_submitted_request"]["skill"]
                  and not row["markers_in_submitted_request"]["config"] and not row["tool_names"]
                  for row in rows)
    report = {"generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "cli_version": agent.version, "success": success, "rows": rows,
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ("tahu/agent.py", "tahu/isolation.py", "scripts/probe_startup.py")},
              "live_model_calls": 0, "real_credentials_used": False, "third_party_deliveries": 0,
              "scope": "developer-authored synthetic native-CLI request capture; not independent or exhaustive attestation",
              "limitations": ["Custom loopback provider, not production service transport",
                              "Built-in CLI instructions remain; request bytes are not token estimates",
                              "Managed machine policy and other installations are not attested"]}
    (ROOT / args.output).write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
