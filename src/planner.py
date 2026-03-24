"""Build a structured analysis plan from parser specification output."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List

_STAT_ORDER = ["count", "mean", "sd", "median", "min", "max"]
_CONTINUOUS_GROUP_HINTS = ("age", "weight", "height", "bmi", "body mass index")
_CATEGORICAL_GROUP_HINTS = ("sex", "ethnicity", "race", "age group")


def _normalize(text: str) -> str:
    return str(text or "").strip().lower()


def _table_title(spec: Dict[str, Any]) -> str:
    doc = spec.get("document_structure", {})
    title = str(doc.get("title", "")).strip()
    if title:
        return title

    source = str(spec.get("source_file", "")).strip()
    if source:
        return Path(source).stem

    return "unknown_table"


def _detect_stats(subrows: List[str]) -> List[str]:
    found = {key: False for key in _STAT_ORDER}

    for raw in subrows:
        label = _normalize(raw).replace("–", "-").replace("—", "-")
        if not label:
            continue

        if label == "n" or " n " in f" {label} ":
            found["count"] = True
        if "mean" in label:
            found["mean"] = True
        if "sd" in label:
            found["sd"] = True
        if "mean (sd)" in label or "mean(sd)" in label:
            found["mean"] = True
            found["sd"] = True
        if "median" in label:
            found["median"] = True
        if "min-max" in label or "minmax" in label or "range" in label:
            found["min"] = True
            found["max"] = True

    return [stat for stat in _STAT_ORDER if found[stat]]


def _has_non_count_continuous_stats(subrows: List[str]) -> bool:
    continuous_stats = {"mean", "sd", "median", "min", "max"}
    return any(stat in continuous_stats for stat in _detect_stats(subrows))


def _is_stat_like_label(label: str) -> bool:
    normalized = _normalize(label).replace("–", "-").replace("—", "-")
    if not normalized:
        return False
    if normalized == "n" or " n " in f" {normalized} ":
        return True
    stat_tokens = ("mean", "sd", "median", "min", "max", "range")
    return any(token in normalized for token in stat_tokens)


def _looks_like_category_label(label: str) -> bool:
    normalized = _normalize(label)
    if not normalized or _is_stat_like_label(normalized):
        return False
    if re.search(r"[a-z]", normalized):
        return True
    return bool(re.search(r"[<>=≤≥-]", normalized))


def _is_categorical_group(group_name: str, subrows: List[str]) -> bool:
    name = _normalize(group_name)
    if any(hint in name for hint in _CATEGORICAL_GROUP_HINTS):
        return True

    if not subrows or _has_non_count_continuous_stats(subrows):
        return False

    category_like = [label for label in subrows if _looks_like_category_label(label)]
    return bool(category_like) and len(category_like) >= len(subrows) / 2


def _is_continuous_group(group_name: str, subrows: List[str]) -> bool:
    name = _normalize(group_name)
    has_continuous_name = any(hint in name for hint in _CONTINUOUS_GROUP_HINTS)
    has_continuous_subrows = _has_non_count_continuous_stats(subrows)
    return has_continuous_name or has_continuous_subrows


def build_analysis_plan(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Create a planning-friendly structure from parser spec output."""
    table_shells = spec.get("table_shells", []) or []

    treatment_columns: List[str] = []
    continuous_sections: List[Dict[str, Any]] = []
    categorical_sections: List[Dict[str, Any]] = []
    unresolved_items: List[Dict[str, str]] = []

    for shell in table_shells:
        for column in shell.get("columns", []) or []:
            if column not in treatment_columns:
                treatment_columns.append(column)

        for group in shell.get("row_groups", []) or []:
            name = str(group.get("name", "")).strip()
            subrows = [str(item).strip() for item in group.get("subrows", []) if str(item).strip()]
            if not name:
                continue

            if _is_categorical_group(name, subrows):
                categorical_sections.append(
                    {
                        "name": name,
                        "categories": subrows,
                        "candidate_variable": None,
                    }
                )
                continue

            if _is_continuous_group(name, subrows):
                continuous_sections.append(
                    {
                        "name": name,
                        "subrows": subrows,
                        "statistics": _detect_stats(subrows),
                        "candidate_variable": None,
                    }
                )
                continue

            unresolved_items.append(
                {
                    "type": "classification",
                    "message": f"Could not classify section '{name}' as continuous or categorical.",
                }
            )

    for warning in spec.get("warnings", []) or []:
        unresolved_items.append({"type": "warning", "message": str(warning)})

    doc = spec.get("document_structure", {})
    missing_fields = set(spec.get("missing_fields", []) or [])
    if not doc.get("population") or "population" in missing_fields:
        unresolved_items.append(
            {
                "type": "missing_population",
                "message": "Population is missing from the parser spec.",
            }
        )

    for question in spec.get("clarification_questions", []) or []:
        unresolved_items.append({"type": "clarification", "message": str(question)})

    requested_statistics = list(spec.get("summary_requirements", []) or [])
    if not requested_statistics:
        derived_stats = []
        for section in continuous_sections:
            for stat in section.get("statistics", []):
                if stat not in derived_stats:
                    derived_stats.append(stat)
        requested_statistics = derived_stats

    assumptions = list(spec.get("proposed_assumptions", []) or [])

    return {
        "table_title": _table_title(spec),
        "dataset_hint": None,
        "treatment_columns": treatment_columns,
        "continuous_sections": continuous_sections,
        "categorical_sections": categorical_sections,
        "requested_statistics": requested_statistics,
        "unresolved_items": unresolved_items,
        "assumptions": assumptions,
    }
