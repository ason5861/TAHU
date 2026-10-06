"""Run a separate gateway process and exercise real HTTP requests, no live LLM."""
import json
import secrets
import subprocess
import sys
import tempfile
from pathlib import Path

from tahu.client import Client


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="tahu_demo_") as temp:
        state = Path(temp)
        credential = secrets.token_urlsafe(48)
        (state / "operator.json").write_text(json.dumps({"token": credential}), encoding="utf-8")
        process = subprocess.Popen([sys.executable, "-B", "-m", "tahu", "serve", "--state", temp, "--port", "0"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Server prints this line only after binding the listening socket.
            line = process.stdout.readline()
            if not line.startswith("TAHU listening on "):
                raise RuntimeError("Gateway failed to start: " + line)
            url = line.split(" on ", 1)[1].split(";", 1)[0]
            operator = Client(url, credential)
            def create(name, sensitive):
                artifacts = [{"id": "public", "text": "Public information", "labels": []}]
                if sensitive:
                    artifacts.append({"id": "private", "text": "SYNTHETIC SECRET", "labels": ["restricted"]})
                result = operator.call("/v1/tasks", {"id": name, "purpose": "Synthetic demonstration", "budget": 20, "attempt_limit": 40, "ttl": 300, "destinations": {"public": [], "internal": ["restricted"]}, "artifacts": artifacts})
                return Client(url, result["token"])
            sensitive = create("sensitive", True)
            public = create("public_only", False)
            checks = []
            def check(label, result, expected):
                passed = result["allowed"] is expected
                checks.append({"check": label, "passed": passed, "reason": result["reason"]})
                if not passed:
                    raise RuntimeError(label + " failed")
            check("read authorized secret", sensitive.step({"request_id": "1", "op": "read", "id": "private"}), True)
            check("derive with omitted provenance", sensitive.step({"request_id": "2", "op": "derive", "id": "draft", "sources": [], "text": "SYNTHETIC SECRET"}), True)
            check("block unapproved exfiltration", sensitive.step({"request_id": "3", "op": "send", "id": "draft", "destination": "public"}), False)
            check("separate public task remains usable", public.step({"request_id": "1", "op": "send", "id": "public", "destination": "public"}), True)
            operator.call("/v1/approve", {"task": "sensitive", "artifact": "draft", "destination": "public", "ttl": 60})
            check("exact operator-approved release", sensitive.step({"request_id": "4", "op": "send", "id": "draft", "destination": "public"}), True)
            check("approval cannot be reused", sensitive.step({"request_id": "5", "op": "send", "id": "draft", "destination": "public"}), False)
            operator.call("/v1/stop", {"task": "sensitive"})
            check("stopped task cannot read", sensitive.step({"request_id": "6", "op": "read", "id": "public"}), False)
            audit = operator.call("/v1/audit/verify", {})
            if not audit["valid"]:
                raise RuntimeError("Audit verification failed")
            print(json.dumps({"checks": checks, "audit_valid": audit["valid"], "deliveries": len(operator.call("/v1/outbox", {})["items"]), "live_model_calls": 0, "external_deliveries": 0}, indent=2))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            process.stdout.close()
            process.stderr.close()


if __name__ == "__main__":
    main()
