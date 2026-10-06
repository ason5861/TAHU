"""Write a machine-readable report from unittest results; never use bare assert."""
import argparse
import contextlib
import datetime
import io
import json
import os
import platform
import subprocess
import sys
import unittest
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="reports/latest.json")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(str(root / "tests"), top_level_dir=str(root))
    output = io.StringIO()
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    print(output.getvalue())
    demo = subprocess.run([sys.executable, "-B", "-m", "examples.demo"], cwd=root, capture_output=True, text=True, timeout=30)
    report = {"version": "0.3.0", "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "python": platform.python_version(), "platform": platform.system(),
              "tests_run": result.testsRun, "failures": len(result.failures), "errors": len(result.errors), "skipped": len(result.skipped),
              "tests_passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
              "container_tests_enabled": bool(os.environ.get("TAHU_TEST_IMAGE")),
              "success": result.wasSuccessful() and demo.returncode == 0, "live_model_calls": 0,
              "external_deliveries": 0, "evaluation_scope": "developer-authored regression and HTTP integration tests",
              "demo": json.loads(demo.stdout) if demo.returncode == 0 else {"error": demo.stderr},
              "known_limitations": ["No live-model evaluation", "Optional Docker isolation requires real-container validation; no kernel-escape guarantee", "Conservative overblocking within sensitive tasks", "Outbox is local only", "Not an independent safety benchmark"]}
    destination = root / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({"success": report["success"], "tests_run": report["tests_run"], "report": args.output}))
    raise SystemExit(0 if report["success"] else 1)


if __name__ == "__main__":
    main()
