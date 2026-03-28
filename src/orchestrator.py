"""Orchestration for docx + csv-schema to R generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.code_generator import generate_r_code
from src.llm_agent import LLMDecisionEngine, LLMUnavailableError
from src.mapper import map_docx_fields_to_csv
from src.parser import parse_inputs
from src.planner import build_generation_plan
from src.validator import validate_code_against_blueprint

try:
    from src.reviewer import review_generation
except Exception:  # pragma: no cover
    review_generation = None


@dataclass
class OrchestrationResult:
    parsed: Any | None
    planned: Any | None
    mapped: Any | None
    generation: Any | None
    review: Any | None
    stopped_stage: str | None
    error_message: str | None
    success: bool


def run_pipeline(
    docx_filename: str,
    csv_path: str,
    trt_group_name: str,
    data_dir: str = "data",
    max_revision_rounds: int = 1,
    model: str = "gpt-4.1-mini",
    enable_reviewer: bool = True,
) -> OrchestrationResult:
    """Run schema-only parse -> map -> generate -> review pipeline."""
    parsed: Any | None = None
    planned: Any | None = None
    mapped: Any | None = None
    generation: Any | None = None
    review: Any | None = None

    try:
        parsed = parse_inputs(docx_filename=docx_filename, csv_path=csv_path, data_dir=data_dir)
    except Exception as exc:
        return OrchestrationResult(parsed, planned, mapped, generation, review, "parser", str(exc), False)

    try:
        planned = build_generation_plan(parsed=parsed, trt_group_name=trt_group_name)
    except Exception as exc:
        return OrchestrationResult(parsed, planned, mapped, generation, review, "planner", str(exc), False)

    try:
        llm_engine = LLMDecisionEngine(model=model)
    except LLMUnavailableError as exc:
        return OrchestrationResult(
            parsed,
            planned,
            mapped,
            generation,
            review,
            "mapper",
            str(exc),
            False,
        )

    feedback: list[str] = []
    validated = False
    for _ in range(max(1, max_revision_rounds + 1)):
        try:
            mapped = map_docx_fields_to_csv(
                plan=planned,
                llm_engine=llm_engine,
                feedback=feedback,
            )
            generation = generate_r_code(
                mapped,
                llm_engine=llm_engine,
                feedback=feedback,
            )
        except Exception as exc:
            return OrchestrationResult(
                parsed,
                planned,
                mapped,
                generation,
                review,
                "generation",
                str(exc),
                False,
            )

        validation = validate_code_against_blueprint(generation.code, mapped)
        if not validation.ok:
            feedback = list(validation.issues)
            review = None
            continue
        validated = True

        if enable_reviewer and callable(review_generation):
            try:
                review = review_generation(generation)
            except Exception as exc:
                feedback.append(f"Reviewer error: {exc}")
                review = None
        else:
            review = None

        if review is None or getattr(review, "status", "fail") != "fail":
            break
        feedback = list(getattr(review, "issues", []) or []) + list(
            getattr(review, "warnings", []) or []
        )

    # Reviewer is optional; structural validation is required.
    success = generation is not None and validated
    stopped_stage = None

    return OrchestrationResult(
        parsed=parsed,
        planned=planned,
        mapped=mapped,
        generation=generation,
        review=review,
        stopped_stage=stopped_stage,
        error_message=None if success else "Generated code did not satisfy blueprint validation.",
        success=success,
    )
