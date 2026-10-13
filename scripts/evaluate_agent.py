"""Explicit opt-in live evaluation. Never calls a model in default CI."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tahu.agent import CodexAgent
from tahu.evaluation import run_evaluation


def main():
    parser = argparse.ArgumentParser(description="Evaluate real Codex proposals using synthetic data and local outbox delivery")
    parser.add_argument("--live", action="store_true", help="Required opt-in: consumes your authenticated Codex usage")
    parser.add_argument("--model", required=True)
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--max-turns", type=int, default=2)
    parser.add_argument("--case", action="append", dest="selected")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--output", default="reports/live-agent.json")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; this command consumes authenticated model usage")
    def progress(row):
        print(json.dumps({"case": row["case"], "repeat": row["repeat"], "turn": row["turn"],
                          "result": row.get("error", row.get("decision", {}).get("reason"))}), flush=True)
    report = run_evaluation(CodexAgent(args.model, args.timeout), args.repeats, args.max_turns, args.selected, progress)
    path = ROOT / args.output
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    raise SystemExit(1 if report["summary"]["errors"] or report["summary"]["missed_blocks"] or not report["audit"]["valid"] else 0)


if __name__ == "__main__":
    main()
