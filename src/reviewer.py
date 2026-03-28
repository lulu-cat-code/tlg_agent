"""Review generated R script readiness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class ReviewResult:
    status: Literal["pass", "warn", "fail"]
    issues: list[str]
    warnings: list[str]
    suggestions: list[str]


def _has_executable_code(code: str) -> bool:
    for raw in str(code or "").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return True
    return False


def review_generation(generation: Any) -> ReviewResult:
    code = str(getattr(generation, "code", "") or "")
    unresolved = list(getattr(generation, "unresolved_mappings", []) or [])
    generation_warnings = [str(item) for item in list(getattr(generation, "warnings", []) or [])]

    issues: list[str] = []
    warnings: list[str] = list(generation_warnings)
    suggestions: list[str] = []

    if unresolved:
        issues.append("Unresolved mappings: " + ", ".join(sorted(set(unresolved))))
        suggestions.append("Provide confirmed CSV mappings for unresolved DOCX groups.")

    if "# TODO" in code:
        warnings.append("Generated script still contains TODO markers.")
        suggestions.append("Resolve TODO mapping items before production run.")

    if not _has_executable_code(code):
        issues.append("Generated script contains no executable statements.")
        suggestions.append("Re-run generation with valid DOCX/CSV schema inputs.")

    status: Literal["pass", "warn", "fail"]
    if issues:
        status = "fail"
    elif warnings:
        status = "warn"
    else:
        status = "pass"

    return ReviewResult(
        status=status,
        issues=issues,
        warnings=warnings,
        suggestions=suggestions,
    )
