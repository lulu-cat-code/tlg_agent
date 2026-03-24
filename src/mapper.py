"""Map planner sections to candidate analysis variables."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict


_SECTION_TO_VARIABLE = {
    "age (yr)": "AGE",
    "weight (kg) at (timepoint)": "WEIGHT",
    "sex": "SEX",
    "race": "RACE",
    "ethnicity": "ETHNIC",
    "age group (yr)": "AGEGR1",
}


def _normalize(text: str) -> str:
    return str(text or "").strip().lower()


def _mapped_variable(section_name: str) -> str | None:
    return _SECTION_TO_VARIABLE.get(_normalize(section_name))


def map_candidate_variables(plan: Dict[str, Any]) -> Dict[str, Any]:
    """Return the same plan shape with candidate_variable filled when known."""
    mapped_plan = deepcopy(plan)

    for section in mapped_plan.get("continuous_sections", []) or []:
        mapped = _mapped_variable(str(section.get("name", "")))
        if mapped:
            section["candidate_variable"] = mapped
        else:
            section.setdefault("candidate_variable", None)

    for section in mapped_plan.get("categorical_sections", []) or []:
        mapped = _mapped_variable(str(section.get("name", "")))
        if mapped:
            section["candidate_variable"] = mapped
        else:
            section.setdefault("candidate_variable", None)

    return mapped_plan
