"""Build generation plan from DOCX blueprint + CSV schema (no hardcoded semantics)."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def _normalize(text: str) -> str:
    return str(text or "").strip().lower()


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _normalize(text)).strip("_") or "field"


def build_generation_plan(parsed: Dict[str, Any], trt_group_name: str) -> Dict[str, Any]:
    """Create structure-only plan for LLM mapping + code generation."""
    docx_spec = parsed["docx_spec"]
    csv_schema = parsed["csv_schema"]

    mapping_tasks: List[Dict[str, Any]] = []
    tables_plan: List[Dict[str, Any]] = []

    for table_index, table in enumerate(docx_spec.get("table_shells", []), start=1):
        group_info: Dict[str, Dict[str, Any]] = {}
        for group in table.get("row_groups", []):
            group_name = str(group.get("name", "")).strip()
            subrows = [str(row).strip() for row in group.get("subrows", []) if str(row).strip()]
            if not group_name:
                continue
            group_info[group_name] = {"group_type": None, "subrows": subrows}
            mapping_tasks.append(
                {
                    "table_index": table_index,
                    "group_name": group_name,
                    "group_slug": _slugify(group_name),
                    "group_type": None,
                    "candidate_csv_column": None,
                    "category_value_map": {},
                    "confidence": 0.0,
                    "reason": "",
                }
            )

        tables_plan.append(
            {
                "table_index": table_index,
                "columns": list(table.get("columns", [])),
                "group_sizes": dict(table.get("group_sizes", {})),
                "ordered_rows": list(table.get("ordered_rows", [])),
                "group_info": group_info,
            }
        )

    return {
        "title": docx_spec.get("document", {}).get("title", ""),
        "docx_source": docx_spec.get("source_file", ""),
        "csv_schema": csv_schema,
        "trt_group_name": trt_group_name,
        "tables": tables_plan,
        "mapping_tasks": mapping_tasks,
        "output_contract": {
            "preserve_docx_order": True,
            "preserve_docx_columns": True,
            "format_required": True,
        },
        "unresolved": [],
    }
