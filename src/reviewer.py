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
    unresolved_dependencies = list(getattr(generation, "unresolved_dependencies", []) or [])
    generation_warnings = [str(item) for item in list(getattr(generation, "warnings", []) or [])]

    issues: list[str] = []
    warnings: list[str] = list(generation_warnings)
    suggestions: list[str] = []

    if unresolved:
        issues.append("Unresolved mappings: " + ", ".join(sorted(set(unresolved))))
        suggestions.append("Provide confirmed CSV mappings for unresolved DOCX groups.")

    if unresolved_dependencies:
        issues.append("Unresolved dependencies: " + ", ".join(sorted(set(unresolved_dependencies))))
        suggestions.append(
            "Resolve all dependencies in generation.unresolved_dependencies before execution."
        )

    if "# TODO" in code:
        warnings.append("Generated code still contains TODO markers.")
        suggestions.append("Resolve TODO markers in generated code.")

    if not _has_executable_code(code):
        issues.append("Generated code is empty or only comments.")
        suggestions.append("Generate executable R statements before release.")

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
