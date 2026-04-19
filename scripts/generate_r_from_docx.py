#!/usr/bin/env python3
"""Generate R code from DOCX shell + CSV schema + TRT group name."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.orchestrator import run_pipeline


def _expand_mapping_text(value: str) -> str:
    text = str(value or "").lower()
    text = text.replace("bp", "blood pressure")
    text = text.replace("wt", "weight")
    return text


def _tokenize_mapping_text(value: str) -> set[str]:
    expanded = _expand_mapping_text(value)
    raw_tokens = re.findall(r"[a-z]+", expanded)
    normalized_tokens: list[str] = []
    for token in raw_tokens:
        if token.startswith("agegr"):
            normalized_tokens.extend(["age", "group"])
            continue
        if token == "ethnic":
            normalized_tokens.append("ethnicity")
            continue
        normalized_tokens.append(token)
    stopwords = {
        "at",
        "and",
        "or",
        "the",
        "of",
        "group",
        "patients",
        "patient",
        "baseline",
        "yr",
        "kg",
    }
    return {token for token in normalized_tokens if token not in stopwords}


def _find_suspicious_mappings(mapped: Any) -> list[tuple[str, str]]:
    suspicious: list[tuple[str, str]] = []
    for task in list((mapped or {}).get("mapping_tasks", []) or []):
        group_name = str(task.get("group_name", "")).strip()
        candidate = str(task.get("candidate_csv_column", "")).strip()
        if not group_name or not candidate:
            continue
        group_tokens = _tokenize_mapping_text(group_name)
        candidate_tokens = _tokenize_mapping_text(candidate)
        if group_tokens and candidate_tokens and group_tokens.isdisjoint(candidate_tokens):
            suspicious.append((group_name, candidate))
    return suspicious


def _build_todo_markdown(
    *,
    docx_filename: str,
    csv_path: str,
    trt_group_name: str,
    review: Any,
    mapped: Any,
) -> str:
    lines = ["# Review Before Re-run", ""]
    must_fix: list[str] = []
    please_check: list[str] = []

    for group_name, candidate in _find_suspicious_mappings(mapped):
        must_fix.append(
            f"- {group_name}: mapped to `{candidate}`, which may not match the section meaning."
        )

    warnings = [str(item) for item in list(getattr(review, "warnings", []) or [])]
    for warning in warnings:
        if "TODO" in warning:
            please_check.append(
                "- Generated code still contains TODO fallback branches. "
                "If the final output shows any `TODO`, update the shell labels or CSV column names and submit again."
            )
        else:
            please_check.append(f"- {warning}")

    if must_fix:
        lines.append("## Must Fix")
        lines.extend(must_fix)
        lines.append("")

    if please_check:
        lines.append("## Please Check")
        lines.extend(please_check)
        lines.append("")

    lines.append("## Re-run")
    lines.append(
        f"- After updating `{docx_filename}` or `{csv_path}`, submit the same inputs again with treatment column `{trt_group_name}`."
    )
    lines.append("")
    return "\n".join(lines)


def _generated_at_line() -> str:
    return f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


def _todo_output_path(output_path: Path) -> Path:
    return output_path.with_suffix(".todo.md")


def _result_output_path(output_path: Path) -> Path:
    return output_path.with_suffix(".result.json")


def _actionable_todo_markdown(
    *,
    docx_filename: str,
    csv_path: str,
    trt_group_name: str,
    review: Any,
    mapped: Any,
    validation_issues: list[str] | None = None,
) -> str | None:
    suspicious = _find_suspicious_mappings(mapped)
    must_fix = [
        f"- {group_name}: mapped to `{candidate}`, which may not match the section meaning."
        for group_name, candidate in suspicious
    ]

    actionable_checks: list[str] = []
    for issue in list(validation_issues or []):
        actionable_checks.append(f"- {issue}")
    for issue in list(getattr(review, "issues", []) or []):
        actionable_checks.append(f"- {issue}")

    if not must_fix and not actionable_checks:
        return None

    lines = ["# Review Before Re-run", ""]
    if must_fix:
        lines.append("## Must Fix")
        lines.extend(must_fix)
        lines.append("")

    if actionable_checks:
        lines.append("## Please Check")
        lines.extend(actionable_checks)
        lines.append("")

    lines.append("## Re-run")
    lines.append(
        f"- After updating `{docx_filename}` or `{csv_path}`, submit the same inputs again with treatment column `{trt_group_name}`."
    )
    lines.append("")
    return "\n".join(lines)


def _default_todo_markdown(
    *,
    docx_filename: str,
    csv_path: str,
    trt_group_name: str,
    validation_issues: list[str] | None = None,
) -> str:
    details = list(validation_issues or [])
    return "\n".join(
        [
            "# Review Before Re-run",
            "",
            *(details if details else ["No action items."]),
            "",
            "## Re-run",
            f"- Current inputs: `{docx_filename}` and `{csv_path}` with treatment column `{trt_group_name}`.",
            "",
        ]
    )


def _with_generated_at_header(markdown: str) -> str:
    return "\n".join([_generated_at_line(), "", markdown])


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
    output_path = Path(args.output)
    result_path = _result_output_path(output_path)

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
        failure_payload = {
            "docx_filename": args.docx_filename,
            "csv_path": args.csv_path,
            "trt_group_name": args.trt_group_name,
            "output_r_path": str(output_path),
            "pipeline_success": False,
            "review_status": getattr(result.review, "status", "unknown"),
            "issues": list(result.validation_issues or []),
            "warnings": [],
            "todo_path": None,
            "error_message": result.error_message,
            "stopped_stage": result.stopped_stage,
            "usage": result.usage_summary,
        }
        result_path.write_text(json.dumps(failure_payload, indent=2), encoding="utf-8")
        print(f"pipeline failed at: {result.stopped_stage}")
        print(f"error: {result.error_message}")
        print(f"result_written: {result_path}")
        return 1

    output_path.write_text(result.generation.code, encoding="utf-8")

    print(f"written: {output_path}")
    print(f"pipeline_success: {result.success}")
    print(f"review_status: {getattr(result.review, 'status', 'unknown')}")

    issues = list(result.validation_issues or []) + list(getattr(result.review, "issues", []) or [])
    warnings = list(getattr(result.review, "warnings", []) or [])
    todo_path = _todo_output_path(output_path)
    todo_markdown = _actionable_todo_markdown(
        docx_filename=args.docx_filename,
        csv_path=args.csv_path,
        trt_group_name=args.trt_group_name,
        review=result.review,
        mapped=result.mapped,
        validation_issues=result.validation_issues,
    )
    if todo_markdown is None:
        todo_markdown = _default_todo_markdown(
            docx_filename=args.docx_filename,
            csv_path=args.csv_path,
            trt_group_name=args.trt_group_name,
            validation_issues=result.validation_issues,
        )
    todo_path.write_text(_with_generated_at_header(todo_markdown), encoding="utf-8")
    print(f"todo_written: {todo_path}")

    result_payload = {
        "docx_filename": args.docx_filename,
        "csv_path": args.csv_path,
        "trt_group_name": args.trt_group_name,
        "output_r_path": str(output_path),
        "pipeline_success": bool(result.success),
        "review_status": getattr(result.review, "status", "unknown"),
        "issues": issues,
        "warnings": warnings,
        "todo_path": str(todo_path),
        "error_message": result.error_message,
        "usage": result.usage_summary,
    }
    result_path.write_text(json.dumps(result_payload, indent=2), encoding="utf-8")
    print(f"result_written: {result_path}")
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
