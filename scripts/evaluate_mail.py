"""Explicit opt-in independent model comparison and local SMTP delivery."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tahu.agent import CodexAgent
from tahu.mail_evaluation import run_mail_evaluation


def main():
    parser = argparse.ArgumentParser(description="Compare three independent live agent arms with synthetic local mail")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", default="reports/mail-agent.json")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live required: consumes authenticated Codex usage")
    def progress(row):
        print(json.dumps({"case": row["case"], "arm": row["arm"], "result": row.get("error", row.get("decision", {}).get("reason")),
                          "delivered": row["delivered"]}), flush=True)
    report = run_mail_evaluation(CodexAgent(args.model, args.timeout), args.repeats, progress)
    destination = ROOT / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(report["summary"], indent=2))
    # Baseline policy violations are measurements, not harness errors. TAHU must
    # not leak. Below-target utility is reported even when the harness exits 0.
    raise SystemExit(1 if any(value["errors"] for value in report["summary"].values())
                     or report["summary"]["tahu"]["unauthorized_deliveries"] or not report["audit"]["valid"] else 0)


if __name__ == "__main__":
    main()
