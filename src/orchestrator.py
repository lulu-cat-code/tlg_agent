"""Orchestration for docx + csv-schema to R generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.code_generator import generate_r_code
from src.llm_agent import LLMDecisionEngine, LLMUnavailableError
from src.mapper import map_candidate_variables, map_docx_fields_to_csv
from src.parser import interpret_parser_spec, parse_inputs
from src.planner import build_analysis_plan, build_generation_plan
from src.runner import run_r_code
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
    run_result: Any | None
    stopped_stage: str | None
    error_message: str | None
    success: bool


def run_pipeline(
    docx_filename: str,
    csv_path: str | None = None,
    trt_group_name: str | None = None,
    data_dir: str = "data",
    max_revision_rounds: int = 1,
    model: str = "gpt-4.1-mini",
    enable_reviewer: bool = True,
) -> OrchestrationResult:
    """Run either the legacy text pipeline or the current schema-driven pipeline."""
    parsed: Any | None = None
    planned: Any | None = None
    mapped: Any | None = None
    generation: Any | None = None
    review: Any | None = None
    run_result: Any | None = None

    if csv_path is None or trt_group_name is None:
        try:
            parsed = interpret_parser_spec(docx_filename)
            planned = build_analysis_plan(parsed)
            mapped = map_candidate_variables(planned)
            generation = generate_r_code(mapped)
            review = review_generation(generation) if callable(review_generation) else None
            if review is not None and getattr(review, "status", "fail") == "fail":
                return OrchestrationResult(
                    parsed, planned, mapped, generation, review, None, "reviewer", None, False
                )
            run_result = run_r_code(generation.code)
            return OrchestrationResult(
                parsed=parsed,
                planned=planned,
                mapped=mapped,
                generation=generation,
                review=review,
                run_result=run_result,
                stopped_stage=None,
                error_message=None,
                success=bool(run_result and run_result.success),
            )
        except Exception as exc:
            stage = "mapper" if parsed is not None and planned is not None else "parser"
            return OrchestrationResult(
                parsed=parsed,
                planned=planned,
                mapped=mapped,
                generation=generation,
                review=review,
                run_result=run_result,
                stopped_stage=stage,
                error_message=str(exc),
                success=False,
            )

    try:
        parsed = parse_inputs(docx_filename=docx_filename, csv_path=csv_path, data_dir=data_dir)
    except Exception as exc:
        return OrchestrationResult(parsed, planned, mapped, generation, review, run_result, "parser", str(exc), False)

    try:
        planned = build_generation_plan(parsed=parsed, trt_group_name=trt_group_name)
    except Exception as exc:
        return OrchestrationResult(parsed, planned, mapped, generation, review, run_result, "planner", str(exc), False)

    try:
        llm_engine = LLMDecisionEngine(model=model)
    except LLMUnavailableError as exc:
        return OrchestrationResult(
            parsed,
            planned,
            mapped,
            generation,
            review,
            run_result,
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
                run_result,
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
        run_result=run_result,
        stopped_stage=stopped_stage,
        error_message=None if success else "Generated code did not satisfy blueprint validation.",
        success=success,
    )
