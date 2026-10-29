"""At most three synthetic drafting calls; stop on first error, never send mail."""
import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tahu.agent import CodexAgent, error_code
from tahu.mail_evaluation import drafting_job, load_corpus

# Fixed before execution. A repeat tests intermittency without changing inputs.
PLAN = ("internal_reply", "public_reply", "internal_reply")


def run(provider):
    corpus, corpus_hash = load_corpus()
    cases = {case["id"]: case for case in corpus["cases"]}
    rows, stopped = [], False
    for position, case_id in enumerate(PLAN):
        job = drafting_job(cases[case_id])
        row = {"position": position, "case": case_id,
               "job_sha256": hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest(),
               "status": "not_attempted" if stopped else "attempted"}
        if not stopped:
            started = time.perf_counter()
            try:
                row["result"] = provider.propose(job)
                row["status"] = "completed"
            except (OSError, RuntimeError, ValueError) as exc:
                row["error"] = error_code(exc)
                row["status"] = "error"
                stopped = True
            row["elapsed_seconds"] = round(time.perf_counter() - started, 6)
        rows.append(row)
    return {"protocol": "lifecycle-drafting-smoke-v1", "rows": rows,
            "generated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "corpus_sha256": corpus_hash, "planned": len(PLAN),
            "attempted": sum(row["status"] != "not_attempted" for row in rows),
            "passed": all(row["status"] == "completed" for row in rows),
            "conditions": {"timeout_seconds": 120, "calls_per_slot": 1,
                           "harness_retries": 0, "stop_on_first_error": True,
                           "prompt_safeguards": True},
            "source_sha256": {n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest()
                              for n in ("scripts/diagnose_lifecycle.py", "tahu/agent.py", "tahu/isolation.py", "tahu/mail_evaluation.py")},
            "mail_deliveries": 0,
            "limitations": ["Drafting diagnostic only, not a security or utility comparison",
                            "No claim of transport root cause or long-term stability",
                            "Does not replace historical errors or denominators",
                            "Failed-call usage and dollar cost unavailable; CLI-internal retries unmeasured"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if not args.live:
        parser.error("--live required; consumes existing Codex usage")
    report = run(CodexAgent(args.model, timeout=120))
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps({k: report[k] for k in ("planned", "attempted", "passed")}))
    return int(not report["passed"])


if __name__ == "__main__":
    raise SystemExit(main())
