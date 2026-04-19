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
