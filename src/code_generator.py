"""LLM-based R code generator with unresolved-mapping tracking."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from src.llm_agent import LLMDecisionEngine


@dataclass
class GenerationResult:
    code: str
    warnings: list[str]
    unresolved_mappings: list[str]


def _collect_unresolved(plan: Dict[str, Any]) -> list[str]:
    unresolved = set(str(x) for x in list(plan.get("unresolved", []) or []) if str(x).strip())
    for task in plan.get("mapping_tasks", []) or []:
        if not str(task.get("candidate_csv_column", "")).strip():
            unresolved.add(str(task.get("group_name", "")).strip())
    return sorted(x for x in unresolved if x)


def generate_r_code(
    plan: Dict[str, Any],
    llm_engine: LLMDecisionEngine,
    feedback: List[str] | None = None,
) -> GenerationResult:
    """Generate executable R script via LLM from mapped plan."""
    payload = llm_engine.generate_r_script(mapped_plan=plan, feedback=feedback)
    code = str(payload.get("code", "") or "")
    warnings = [str(item) for item in list(payload.get("warnings", []) or [])]
    unresolved = _collect_unresolved(plan)
    return GenerationResult(code=code, warnings=warnings, unresolved_mappings=unresolved)
