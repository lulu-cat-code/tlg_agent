#!/usr/bin/env python3
"""Background generate job runner for the Shiny app."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.job_state import append_event, build_stage_list, utc_now_iso, write_json
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


def _actionable_todo_markdown(
    *,
    docx_filename: str,
    csv_path: str,
    trt_group_name: str,
    review: Any,
    mapped: Any,
) -> str | None:
    suspicious = _find_suspicious_mappings(mapped)
    must_fix = [
        f"- {group_name}: mapped to `{candidate}`, which may not match the section meaning."
        for group_name, candidate in suspicious
    ]

    actionable_checks: list[str] = []
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run a background generate job.")
    parser.add_argument("--job-dir", required=True, help="Job working directory")
    parser.add_argument("--docx-filename", required=True, help="DOCX filename within job dir")
    parser.add_argument("--csv-path", required=True, help="CSV file path")
    parser.add_argument("--trt-group-name", required=True, help="Treatment group column")
    parser.add_argument("--model", default="gpt-4.1-mini", help="LLM model")
    parser.add_argument("--disable-reviewer", action="store_true", help="Disable reviewer stage")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    job_dir = Path(args.job_dir)
    status_path = job_dir / "status.json"
    events_path = job_dir / "events.log"
    output_r_path = job_dir / "generated_shell.R"
    result_json_path = output_r_path.with_suffix(".result.json")
    todo_path = output_r_path.with_suffix(".todo.md")

    started_at = utc_now_iso()

    def write_status(*, status: str, stage: str, message: str, finished_at: str | None = None, error_message: str | None = None, result_available: bool = False) -> None:
        payload = {
            "job_id": job_dir.name,
            "job_type": "generate",
            "status": status,
            "stage": stage,
            "message": message,
            "started_at": started_at,
            "updated_at": utc_now_iso(),
            "finished_at": finished_at,
            "error_message": error_message,
            "result_available": result_available,
            "paths": {
                "job_dir": str(job_dir),
                "events_log": str(events_path),
                "output_r": str(output_r_path),
                "result_json": str(result_json_path),
                "todo_md": str(todo_path),
            },
            "stages": build_stage_list(stage, final_status=status if status in {"succeeded", "failed", "cancelled"} else None),
        }
        write_json(status_path, payload)

    def on_progress(stage: str, message: str) -> None:
        append_event(events_path, message)
        write_status(status="running", stage=stage, message=message)

    write_status(status="queued", stage="queued", message="Job created")
    append_event(events_path, f"Job created for model {args.model}")

    result = run_pipeline(
        docx_filename=args.docx_filename,
        csv_path=args.csv_path,
        trt_group_name=args.trt_group_name,
        data_dir=str(job_dir),
        model=args.model,
        enable_reviewer=not args.disable_reviewer,
        progress_callback=on_progress,
    )

    if result.generation is None:
        failure_payload = {
            "docx_filename": args.docx_filename,
            "csv_path": args.csv_path,
            "trt_group_name": args.trt_group_name,
            "output_r_path": str(output_r_path),
            "pipeline_success": False,
            "review_status": getattr(result.review, "status", "unknown"),
            "issues": [],
            "warnings": [],
            "todo_path": None,
            "error_message": result.error_message,
            "stopped_stage": result.stopped_stage,
            "usage": result.usage_summary,
        }
        write_json(result_json_path, failure_payload)
        append_event(events_path, f"Pipeline failed at {result.stopped_stage}: {result.error_message}")
        write_status(
            status="failed",
            stage=result.stopped_stage or "done",
            message="Generation failed",
            finished_at=utc_now_iso(),
            error_message=result.error_message,
            result_available=True,
        )
        return 1

    output_r_path.write_text(result.generation.code, encoding="utf-8")
    append_event(events_path, f"Generated R script written to {output_r_path.name}")

    issues = list(getattr(result.review, "issues", []) or [])
    warnings = list(getattr(result.review, "warnings", []) or [])
    todo_markdown = _actionable_todo_markdown(
        docx_filename=args.docx_filename,
        csv_path=args.csv_path,
        trt_group_name=args.trt_group_name,
        review=result.review,
        mapped=result.mapped,
    )
    if todo_markdown is not None:
        todo_path.write_text(todo_markdown, encoding="utf-8")
        append_event(events_path, f"Action items written to {todo_path.name}")
    elif todo_path.exists():
        todo_path.unlink()

    result_payload = {
        "docx_filename": args.docx_filename,
        "csv_path": args.csv_path,
        "trt_group_name": args.trt_group_name,
        "output_r_path": str(output_r_path),
        "pipeline_success": bool(result.success),
        "review_status": getattr(result.review, "status", "unknown"),
        "issues": issues,
        "warnings": warnings,
        "todo_path": str(todo_path) if todo_markdown is not None else None,
        "error_message": result.error_message,
        "usage": result.usage_summary,
    }
    write_json(result_json_path, result_payload)
    append_event(events_path, "Generation job completed")
    write_status(
        status="succeeded" if result.success else "failed",
        stage="done",
        message="Generation completed" if result.success else "Generation failed validation",
        finished_at=utc_now_iso(),
        error_message=result.error_message,
        result_available=True,
    )
    return 0 if result.success else 2


if __name__ == "__main__":
    raise SystemExit(main())
