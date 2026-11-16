"""Run the pipeline on every meeting in data/eval/ and print how it did.

Usage: uv run python -m scripts.evaluate [--only planning_01]
Calls the real model, so it needs GEMINI_API_KEY in .env.
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from app.extract import ExtractionError, extract_long
from scripts.scoring import score_meeting

EVAL_DIR = Path("data/eval")
RUNS_DIR = Path("eval_runs")


def run_meeting(name: str) -> dict:
    labels = json.loads((EVAL_DIR / f"{name}.expected.json").read_text(encoding="utf-8"))
    transcript = (EVAL_DIR / f"{name}.txt").read_text(encoding="utf-8")

    start = time.perf_counter()
    error = None
    try:
        items = extract_long(transcript, labels["meeting_date"]).action_items
    except ExtractionError as exc:
        items, error = [], str(exc)
    seconds = time.perf_counter() - start

    return {
        "meeting": name,
        "seconds": round(seconds, 1),
        "error": error,
        **score_meeting(items, labels["action_items"]),
        "extracted": [item.model_dump(mode="json") for item in items],
    }


def pct(part: int, whole: int) -> str:
    return f"{part / whole:.0%}" if whole else "n/a"


def print_report(results: list[dict]) -> None:
    print(f"\n{'meeting':<14}{'found':>8}{'invented':>10}{'dup':>5}{'owner':>8}{'due':>7}{'secs':>7}")
    for r in results:
        found = f"{r['found']}/{r['expected']}"
        print(
            f"{r['meeting']:<14}{found:>8}{r['invented']:>10}{r['duplicates']:>5}"
            f"{r['owner_correct']:>8}{r['due_correct']:>7}{r['seconds']:>7}"
        )
        if r["error"]:
            print(f"   FAILED: {r['error']}")
        for quote in r["missed"]:
            print(f"   missed:   {quote}")
        for quote in r["invented_quotes"]:
            print(f"   invented: {quote}")

    expected = sum(r["expected"] for r in results)
    found = sum(r["found"] for r in results)
    print(f"\nRecall (found):  {found}/{expected} = {pct(found, expected)}")
    print(f"Invented items:  {sum(r['invented'] for r in results)}")
    print(f"Owner correct:   {sum(r['owner_correct'] for r in results)}/{found}")
    print(f"Due correct:     {sum(r['due_correct'] for r in results)}/{found}")
    seconds = [r["seconds"] for r in results]
    print(f"Avg latency:     {sum(seconds) / len(seconds):.1f}s per meeting")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score the pipeline on the eval set.")
    parser.add_argument("--only", help="run a single meeting, e.g. planning_01")
    args = parser.parse_args()

    names = sorted(p.name.removesuffix(".expected.json") for p in EVAL_DIR.glob("*.expected.json"))
    if args.only:
        names = [n for n in names if n == args.only]
    if not names:
        raise SystemExit("No matching meetings in data/eval/")

    results = []
    for name in names:
        print(f"running {name}...", flush=True)
        results.append(run_meeting(name))

    print_report(results)

    RUNS_DIR.mkdir(exist_ok=True)
    out = RUNS_DIR / f"{datetime.now():%Y%m%d_%H%M%S}.json"
    out.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved details to {out}")


if __name__ == "__main__":
    main()
