"""Run extraction on a transcript file.

Usage: uv run python -m scripts.extract_file data/samples/standup_01.txt --date 2026-10-27
"""

import argparse
import logging
from pathlib import Path

from app.extract import extract_long


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract action items from a transcript file.")
    parser.add_argument("path", type=Path, help="Path to a UTF-8 text transcript")
    parser.add_argument("--date", required=True, help="Meeting date, YYYY-MM-DD")
    parser.add_argument("--attempts", type=int, default=3, help="Maximum model attempts")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    transcript = args.path.read_text(encoding="utf-8")
    result = extract_long(transcript, args.date, max_attempts=args.attempts)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
