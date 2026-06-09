#!/usr/bin/env python3
"""CLI: generate N synthetic survey responses.

Examples
--------
    # 200 responses for the demo survey, CSV + JSON, reproducible
    python generate.py --survey survey.json --n 200 --seed 47

    # also rewrite open-text with an LLM (default provider: Gemini, needs GEMINI_API_KEY)
    python generate.py --survey survey.json --n 200 --seed 47 --llm

    # print a few rows to the terminal
    python generate.py --survey survey.json --n 5 --preview --no-files
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys

# Preview output can contain em-dashes etc.; avoid cp1252 console crashes.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from surveygen import load_survey, ResponseGenerator
from surveygen.validate import validate, format_report


def _load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from a local .env into the environment.

    Tiny, dependency-free loader so the documented GEMINI_API_KEY /
    ENABLE_LLM_TEXT workflow works without exporting vars by hand. Variables
    already present in the real environment win, so an explicit export still
    overrides the file.
    """
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding="utf-8") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                os.environ.setdefault(key, value)
    except OSError:
        pass  # a missing/unreadable .env is never fatal


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="Synthetic survey response generator")
    p.add_argument("--survey", default="survey.json", help="Path to survey JSON")
    p.add_argument("--n", type=int, default=200, help="Number of responses")
    p.add_argument("--seed", type=int, default=None, help="RNG seed (reproducible output)")
    p.add_argument("--out-prefix", default="responses", help="Output file prefix")
    p.add_argument("--no-files", action="store_true", help="Do not write output files")
    p.add_argument("--preview", action="store_true", help="Print the first few rows")
    p.add_argument("--preview-n", type=int, default=8, help="Rows to preview")
    p.add_argument("--report", action="store_true", help="Also write a validation report")
    p.add_argument("--llm", action="store_true", help="Rewrite open-text via LLM")
    p.add_argument(
        "--llm-provider",
        default="gemini",
        choices=["gemini", "claude"],
        help="LLM provider for --llm (default: gemini)",
    )
    p.add_argument("--llm-model", default=None, help="Override the LLM model id")
    return p.parse_args(argv)


def write_csv(path, survey, responses):
    # Keep diagnostic underscore-fields out of the deliverable CSV.
    fields = ["respondent_id"] + [q.id for q in survey.questions]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in responses:
            w.writerow(r)


def write_json(path, survey, responses):
    payload = {
        "survey": survey.title,
        "n": len(responses),
        "questions": [{"id": q.id, "text": q.text, "type": q.type} for q in survey.questions],
        "responses": responses,
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)


def main(argv=None) -> int:
    args = parse_args(argv)

    # Pick up GEMINI_API_KEY / ENABLE_LLM_TEXT from a local .env if present.
    _load_dotenv()

    # ENABLE_LLM_TEXT=true in the environment is equivalent to passing --llm.
    if not args.llm and os.environ.get("ENABLE_LLM_TEXT", "").strip().lower() == "true":
        args.llm = True

    survey = load_survey(args.survey)
    gen = ResponseGenerator(survey, seed=args.seed)
    responses = gen.generate(args.n)

    if args.llm:
        from surveygen.llm import augment_open_text, LLMUnavailable, DEFAULT_MODELS
        try:
            provider = args.llm_provider
            model = args.llm_model or DEFAULT_MODELS[provider]
            print(
                f"Augmenting open-text via {provider} ({model})...", file=sys.stderr
            )
            responses = augment_open_text(
                survey, responses, provider=provider, model=model
            )
        except LLMUnavailable as exc:
            print(f"[llm disabled] {exc}", file=sys.stderr)

    print(f"Generated {len(responses)} responses for '{survey.title}'.", file=sys.stderr)

    if not args.no_files:
        write_csv(f"{args.out_prefix}.csv", survey, responses)
        write_json(f"{args.out_prefix}.json", survey, responses)
        print(f"Wrote {args.out_prefix}.csv and {args.out_prefix}.json", file=sys.stderr)

    if args.report:
        report = validate(survey, responses)
        md = format_report(survey, report)
        with open("validation_report.md", "w", encoding="utf-8") as fh:
            fh.write(md)
        print("Wrote validation_report.md", file=sys.stderr)

    if args.preview:
        _preview(survey, responses, args.preview_n)

    return 0


def _preview(survey, responses, k):
    print("\n--- preview ---")
    for r in responses[:k]:
        print(f"\n{r['respondent_id']}  (persona: {r.get('_persona')})")
        for q in survey.questions:
            print(f"  {q.text:<28} {r[q.id]!r}")


if __name__ == "__main__":
    raise SystemExit(main())
