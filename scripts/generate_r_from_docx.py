#!/usr/bin/env python3
"""Generate R code from DOCX shell + CSV schema + TRT group name."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator import run_pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate R code using docx shell + csv schema + trt group name."
    )
    parser.add_argument("docx_filename", help="DOCX shell filename under --data-dir")
    parser.add_argument("csv_path", help="CSV file path (header is enough in schema-only phase)")
    parser.add_argument("trt_group_name", help="Treatment group column name in CSV")
    parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing DOCX shell (default: data)",
    )
    parser.add_argument(
        "--output",
        default="generated.R",
        help="Output R script path (default: generated.R)",
    )
    parser.add_argument(
        "--max-revision-rounds",
        type=int,
        default=1,
        help="Number of feedback revision rounds (default: 1)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4.1-mini",
        help="LLM model name for mapping/classification (default: gpt-4.1-mini)",
    )
    parser.add_argument(
        "--disable-reviewer",
        action="store_true",
        help="Disable reviewer stage (pipeline still generates R code)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    result = run_pipeline(
        docx_filename=args.docx_filename,
        csv_path=args.csv_path,
        trt_group_name=args.trt_group_name,
        data_dir=args.data_dir,
        max_revision_rounds=args.max_revision_rounds,
        model=args.model,
        enable_reviewer=not args.disable_reviewer,
    )

    if result.generation is None:
        print(f"pipeline failed at: {result.stopped_stage}")
        print(f"error: {result.error_message}")
        return 1

    output_path = Path(args.output)
    output_path.write_text(result.generation.code, encoding="utf-8")

    print(f"written: {output_path}")
    print(f"pipeline_success: {result.success}")
    print(f"review_status: {getattr(result.review, 'status', 'unknown')}")

    issues = list(getattr(result.review, "issues", []) or [])
    warnings = list(getattr(result.review, "warnings", []) or [])
    if issues:
        print("issues:")
        for issue in issues:
            print(f"- {issue}")
    if warnings:
        print("warnings:")
        for warning in warnings:
            print(f"- {warning}")

    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
