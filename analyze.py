#!/usr/bin/env python3
"""CLI: validate an existing responses file and print/write a quality report.

    python analyze.py --survey survey.json --responses responses.json
    python analyze.py --survey survey.json --responses responses.json --out validation_report.md
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

# The validation report uses block-bar characters; make sure printing to a
# legacy Windows console (cp1252) doesn't crash.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from surveygen import load_survey
from surveygen.validate import validate, format_report


def load_responses(path: str):
    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data["responses"] if isinstance(data, dict) else data
    # CSV: coerce numeric-looking fields back to ints.
    rows = []
    with open(path, "r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            rows.append({k: _coerce(v) for k, v in row.items()})
    return rows


def _coerce(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return v


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Validate synthetic survey responses")
    p.add_argument("--survey", default="survey.json")
    p.add_argument("--responses", default="responses.json")
    p.add_argument("--out", default=None, help="Write the report to this Markdown file")
    args = p.parse_args(argv)

    survey = load_survey(args.survey)
    responses = load_responses(args.responses)
    report = validate(survey, responses)
    md = format_report(survey, report)

    print(md)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"\n[wrote {args.out}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
