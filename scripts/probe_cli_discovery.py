"""Opt-in Windows npm-layout smoke; installed native CLI, no model or real auth."""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tahu.agent import CodexAgent, resolve_codex_executable
from probe_startup import probe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", action="store_true")
    parser.add_argument("--output", default="reports/cli-discovery.json")
    args = parser.parse_args()
    if not args.capture or sys.platform != "win32":
        parser.error("--capture and Windows required; launches native CLI against loopback only")
    native = resolve_codex_executable()
    with tempfile.TemporaryDirectory(prefix="tahu npm layout ") as directory:
        root = Path(directory)
        shim = root / "codex.cmd"
        sentinel = root / "shim-executed.txt"
        shim.write_text('@echo off\n@echo unexpected>"' + str(sentinel) + '"\n@exit /b 99\n')
        # Use the running Python process architecture for the synthetic layout.
        import platform
        triple = {"amd64": "x86_64", "x86_64": "x86_64", "arm64": "aarch64", "aarch64": "aarch64"}[platform.machine().lower()] + "-pc-windows-msvc"
        package = root / "node_modules" / "@openai" / "codex"
        binary = package / "vendor" / triple / "codex" / "codex.exe"
        binary.parent.mkdir(parents=True)
        (package / "package.json").write_text('{"name":"@openai/codex","version":"synthetic-layout"}')
        shutil.copyfile(native, binary)
        with patch.dict(os.environ, {"PATH": str(root) + os.pathsep + os.environ.get("PATH", "")}):
            found = shutil.which("codex")
            if Path(found).resolve() != shim.resolve():
                raise RuntimeError("fixture_did_not_resolve_npm_shim")
            # The pre-fix initializer rejected this exact discovery result.
            old_rejects = Path(found).suffix.lower() in (".cmd", ".bat")
            agent = CodexAgent("gpt-6.1-sol", 45)
            if Path(agent.executable) != binary.resolve():
                raise RuntimeError("expected_fixture_native_binary")
            rows = [probe(agent, hardened, override) for override in (False, True) for hardened in (False, True)]
        if sentinel.exists():
            raise RuntimeError("npm_shim_executed")
    success = old_rejects and all(
        not any(row["markers_in_submitted_request"].values()) and not row["tool_names"]
        if row["mode"] == "isolated_profile" else
        row["markers_in_submitted_request"]["global"] and row["markers_in_submitted_request"]["skill"] and not row["tool_names"]
        for row in rows)
    report = {"generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "success": success, "cli_version": agent.version,
              "fixture": "synthetic legacy npm layout with copied installed native binary; not an npm installation",
              "old_initializer_rejects": old_rejects, "native_binary_selected": True,
              "shim_executed": False, "rows": rows,
              "live_model_calls": 0, "real_credentials_used": False, "third_party_deliveries": 0,
              "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                                for name in ("tahu/agent.py", "tests/test_cli_discovery.py", "scripts/probe_cli_discovery.py", "scripts/probe_startup.py")},
              "limitations": ["Developer-authored smoke, not independent validation",
                              "Optional npm-package layouts and ARM64 covered by synthetic unit tests only",
                              "No production provider or fresh npm install tested; built-in context remains"]}
    (ROOT / args.output).write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
