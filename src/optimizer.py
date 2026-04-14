"""Conservative optimizer for generated R code."""

from __future__ import annotations

from typing import Any


def simplify_r_code(code: str) -> str:
    """Apply semantics-preserving formatting cleanup."""
    lines = [line.rstrip() for line in str(code or "").splitlines()]

    compact: list[str] = []
    blank_streak = 0
    for line in lines:
        if line == "":
            blank_streak += 1
            if blank_streak <= 1:
                compact.append("")
            continue
        blank_streak = 0
        compact.append(line)

    while compact and compact[-1] == "":
        compact.pop()

    if not compact:
        return ""
    return "\n".join(compact) + "\n"


def optimize_generated_code(generation: Any, mapped_plan: dict[str, Any] | None = None) -> Any:
    """Optimize generated code in-place and return the same generation object."""
    del mapped_plan  # reserved for future optimizer passes
    code = str(getattr(generation, "code", "") or "")
    setattr(generation, "code", simplify_r_code(code))
    return generation
