"""Review generated code and metadata for release readiness."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal


@dataclass
class ReviewResult:
    status: Literal["pass", "warn", "fail"]
    issues: list[str]
    warnings: list[str]
    suggestions: list[str]


def _dedupe_preserve_order(items: Iterable[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return list(value)


def _has_executable_code(code: str) -> bool:
    for raw in str(code or "").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            return True
    return False


def review_generation(generation: Any) -> ReviewResult:
    """Review a GenerationResult-like object and classify readiness."""
    code = str(getattr(generation, "code", "") or "")
    generation_warnings = _as_list(getattr(generation, "warnings", []))
    unsupported_statistics = _as_list(
        getattr(generation, "unsupported_statistics", [])
    )
    unresolved_dependencies = _as_list(
        getattr(generation, "unresolved_dependencies", [])
    )

    issues: list[str] = []
    warnings: list[str] = [str(item) for item in generation_warnings]
    suggestions: list[str] = []

    if unresolved_dependencies:
        issues.append(
            "Unresolved dependencies: "
            + ", ".join(str(item) for item in unresolved_dependencies)
        )
        suggestions.append(
            "Resolve all dependencies in generation.unresolved_dependencies before execution."
        )

    if unsupported_statistics:
        warnings.append(
            "Unsupported statistics present: "
            + ", ".join(str(item) for item in unsupported_statistics)
        )
        suggestions.append(
            "Map or implement unsupported statistics in generation.unsupported_statistics."
        )

    if "# TODO" in code:
        warnings.append("Generated code still contains TODO markers.")
        suggestions.append("Resolve TODO markers in generated code.")

    if "summarise(" in code and '.groups = "drop"' not in code:
        warnings.append('summarise() found without `.groups = "drop"`.')
        suggestions.append('Add `.groups = "drop"` to summarise() calls.')

    if not _has_executable_code(code):
        issues.append("Generated code is empty or only comments.")
        suggestions.append("Generate executable R statements before release.")

    issues = _dedupe_preserve_order(issues)
    warnings = _dedupe_preserve_order(warnings)
    suggestions = _dedupe_preserve_order(suggestions)

    if issues:
        status: Literal["pass", "warn", "fail"] = "fail"
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
