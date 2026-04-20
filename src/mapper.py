"""LLM-backed mapper for DOCX groups to CSV columns."""

from __future__ import annotations

from typing import Any, Dict, List

from src.llm_agent import LLMDecisionEngine


def map_docx_fields_to_csv(
    plan: Dict[str, Any],
    llm_engine: LLMDecisionEngine,
    feedback: List[str] | None = None,
) -> Dict[str, Any]:
    """Use LLM to classify groups, infer row formats, and map CSV columns."""
    return llm_engine.apply(plan=plan, feedback=feedback)


def map_candidate_variables(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Legacy heuristic mapper retained for unit-test compatibility."""
    continuous_map = {
        "age": "AGE",
        "weight": "WEIGHT",
    }
    categorical_map = {
        "sex": "SEX",
        "ethnicity": "ETHNIC",
        "race": "RACE",
        "age group": "AGEGR1",
    }

    mapped = {
        **plan,
        "continuous_sections": [dict(section) for section in plan.get("continuous_sections", [])],
        "categorical_sections": [dict(section) for section in plan.get("categorical_sections", [])],
    }

    for section in mapped["continuous_sections"]:
        name = str(section.get("name", "")).lower()
        for token, variable in continuous_map.items():
            if token in name:
                section["candidate_variable"] = variable
                break

    for section in mapped["categorical_sections"]:
        name = str(section.get("name", "")).lower()
        for token, variable in categorical_map.items():
            if token in name:
                section["candidate_variable"] = variable
                break

    return mapped
