"""Structure validator for generated R code against DOCX blueprint."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List


ALLOWED_R_PACKAGES = {
    "data.table",
    "stats",
    "stringr",
}


@dataclass
class ValidationResult:
    ok: bool
    issues: list[str]


def _contains_hardcoded_example_block(text: str) -> bool:
    patterns = (
        "hardcoded from input json",
        "json_payload <- '{",
        'json_payload <- "{',
        "fromjson(json_payload",
    )
    lowered = text.lower()
    return any(pattern in lowered for pattern in patterns)


def _has_trt_mapping_evidence(text: str) -> bool:
    lowered = text.lower()
    if "trt_group" not in lowered:
        return False

    strong_signals = (
        "trt_levels <- unique(",
        "col_to_trt",
        "column_to_trt",
        "column_map",
        "setnames(",
        "set_names(",
        "match(",
    )
    return any(signal in lowered for signal in strong_signals)


def _has_category_normalization_logic(text: str) -> bool:
    lowered = text.lower()
    normalization_tokens = (
        "tolower(",
        "trimws(",
        "gsub(",
        "sub(",
        "str_replace_all(",
        "str_squish(",
        "stringi::stri_trans_general(",
    )
    return any(token in lowered for token in normalization_tokens)


def _has_runtime_mapped_plan_dependency(text: str) -> bool:
    lowered = text.lower()
    patterns = (
        "mapped_plan$",
        'exists("mapped_plan")',
        "exists('mapped_plan')",
    )
    return any(pattern in lowered for pattern in patterns)


def _find_loaded_packages(text: str) -> set[str]:
    packages: set[str] = set()
    patterns = (
        r"""\blibrary\(\s*['"]?([A-Za-z][A-Za-z0-9.]*)['"]?\s*\)""",
        r"""\brequire\(\s*['"]?([A-Za-z][A-Za-z0-9.]*)['"]?\s*\)""",
    )
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            packages.add(match.group(1))
    return packages


def _find_namespaced_packages(text: str) -> set[str]:
    return {match.group(1) for match in re.finditer(r"\b([A-Za-z][A-Za-z0-9.]*)::[A-Za-z.][A-Za-z0-9._]*", text)}


def _find_disallowed_packages(text: str) -> list[str]:
    used_packages = _find_loaded_packages(text) | _find_namespaced_packages(text)
    return sorted(package for package in used_packages if package not in ALLOWED_R_PACKAGES)


def validate_code_against_blueprint(code: str, mapped_plan: Dict[str, Any]) -> ValidationResult:
    issues: List[str] = []
    text = str(code or "")

    if _contains_hardcoded_example_block(text):
        issues.append("Validator: hardcoded example block detected in generated code.")

    if not _has_trt_mapping_evidence(text):
        issues.append(
            "Validator: missing explicit DOCX-column to TRT-group mapping logic."
        )

    if not _has_category_normalization_logic(text):
        issues.append(
            "Validator: missing category normalization logic (e.g., tolower/trimws/gsub)."
        )

    if _has_runtime_mapped_plan_dependency(text):
        issues.append(
            "Validator: generated code must be self-contained and must not depend on a runtime `mapped_plan` object."
        )

    disallowed_packages = _find_disallowed_packages(text)
    if disallowed_packages:
        issues.append(
            "Validator: disallowed R packages used in generated code: "
            + ", ".join(disallowed_packages)
            + ". Allowed packages: "
            + ", ".join(sorted(ALLOWED_R_PACKAGES))
            + "."
        )

    for table in mapped_plan.get("tables", []) or []:
        table_index = int(table.get("table_index", 0))
        columns = [str(col) for col in list(table.get("columns", []) or []) if str(col).strip()]
        row_labels = [str(row.get("label", "")) for row in list(table.get("ordered_rows", []) or [])]

        for col in columns:
            if col not in text:
                issues.append(f"Table {table_index}: missing column label in generated code: {col}")

        for row_label in row_labels:
            if row_label and row_label not in text:
                issues.append(f"Table {table_index}: missing row label in generated code: {row_label}")

    return ValidationResult(ok=not issues, issues=issues)
