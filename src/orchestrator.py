"""Control-layer orchestration for the TLG-Agent pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.code_generator import generate_r_code
from src.mapper import map_candidate_variables
from src.parser import interpret_parser_spec
from src.planner import build_analysis_plan
from src.reviewer import review_generation
from src.runner import run_r_code


@dataclass
class OrchestrationResult:
    parsed: Any | None
    planned: Any | None
    mapped: Any | None
    generation: Any | None
    review: Any | None
    run_result: Any | None
    stopped_stage: str | None
    error_message: str | None
    success: bool


def _to_normalized_content(shell_text: str) -> dict[str, Any]:
    paragraphs = [line.strip() for line in str(shell_text).splitlines() if line.strip()]
    return {
        "source_file": "<inline_shell_text>",
        "paragraphs": paragraphs,
        "tables": [],
        "footnotes": [],
    }


def run_pipeline(shell_text: str) -> OrchestrationResult:
    """
    Run parser -> planner -> mapper -> code_generator -> reviewer -> runner.

    Adaptation for current repository interface:
    parser.py exposes `interpret_parser_spec(normalized_content)` for in-memory
    content, so `shell_text` is wrapped into a minimal normalized-content dict.
    """
    parsed: Any | None = None
    planned: Any | None = None
    mapped: Any | None = None
    generation: Any | None = None
    review: Any | None = None
    run_result: Any | None = None

    normalized_content = _to_normalized_content(shell_text)

    try:
        parsed = interpret_parser_spec(normalized_content)
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="parser",
            error_message=str(exc),
            success=False,
        )

    try:
        planned = build_analysis_plan(parsed)
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="planner",
            error_message=str(exc),
            success=False,
        )

    try:
        mapped = map_candidate_variables(planned)
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="mapper",
            error_message=str(exc),
            success=False,
        )

    try:
        generation = generate_r_code(mapped)
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="code_generator",
            error_message=str(exc),
            success=False,
        )

    try:
        review = review_generation(generation)
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="reviewer",
            error_message=str(exc),
            success=False,
        )

    if getattr(review, "status", None) == "fail":
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=None,
            stopped_stage="reviewer",
            error_message=None,
            success=False,
        )

    try:
        run_result = run_r_code(getattr(generation, "code", ""))
    except Exception as exc:
        return OrchestrationResult(
            parsed=parsed,
            planned=planned,
            mapped=mapped,
            generation=generation,
            review=review,
            run_result=run_result,
            stopped_stage="runner",
            error_message=str(exc),
            success=False,
        )

    return OrchestrationResult(
        parsed=parsed,
        planned=planned,
        mapped=mapped,
        generation=generation,
        review=review,
        run_result=run_result,
        stopped_stage=None,
        error_message=None,
        success=bool(getattr(run_result, "success", False)),
    )
