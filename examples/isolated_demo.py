"""Offline real-container demo. The probe is deterministic, not an AI model."""
import argparse
import json
import tempfile
from pathlib import Path
from tahu.core import Gateway
from tahu.isolation import DockerWorker, execute_isolated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True, help="immutable sha256 image ID")
    args = parser.parse_args()
    worker = DockerWorker(args.image)
    with tempfile.TemporaryDirectory() as directory:
        gateway = Gateway(Path(directory) / "state.sqlite3")
        outcomes = {}
        for task, labels in (("private", ["restricted"]), ("injected", ["untrusted"]), ("clean", [])):
            gateway.create_task({"id": task, "purpose": "Return the answer to 2 + 2.",
                                 "budget": 10, "attempt_limit": 20, "ttl": 300,
                                 "destinations": {"public": []},
                                 "artifacts": [{"id": "input", "text": "Synthetic input", "labels": labels}]})
            outcomes[task] = execute_isolated(gateway, task, ["input"], "answer", "public", worker)
        expected = (not outcomes["private"]["allowed"] and not outcomes["injected"]["allowed"]
                    and outcomes["clean"]["allowed"] and len(gateway.inspect("outbox")) == 1)
        print(json.dumps({"success": expected, "live_model_calls": 0, "outcomes": outcomes}, indent=2))
        raise SystemExit(0 if expected else 1)


if __name__ == "__main__":
    main()
