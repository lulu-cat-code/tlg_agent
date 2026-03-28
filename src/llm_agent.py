"""LLM-driven semantics and mapping for DOCX shell to CSV schema."""

from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List


class LLMUnavailableError(RuntimeError):
    """Raised when LLM client cannot be initialized."""


def _extract_json(text: str) -> Dict[str, Any]:
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        if raw.startswith("json"):
            raw = raw[4:].strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain JSON object.")
    return json.loads(raw[start : end + 1])


def _to_prompt_payload(plan: Dict[str, Any], feedback: List[str] | None = None) -> Dict[str, Any]:
    csv_columns = [
        str(col.get("name", ""))
        for col in plan.get("csv_schema", {}).get("columns", [])
        if str(col.get("name", "")).strip()
    ]
    tables = []
    for table in plan.get("tables", []):
        tables.append(
            {
                "table_index": table.get("table_index"),
                "columns": table.get("columns", []),
                "row_groups": table.get("group_info", {}),
                "ordered_rows": table.get("ordered_rows", []),
            }
        )
    return {
        "title": plan.get("title", ""),
        "trt_group_name": plan.get("trt_group_name", ""),
        "csv_columns": csv_columns,
        "tables": tables,
        "feedback": feedback or [],
    }


class LLMDecisionEngine:
    """OpenAI-backed decision engine for group typing, row formats, and column mapping."""

    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        self.model = model
        self._client = None
        self._project_root = Path(__file__).resolve().parents[1]
        self._init_client()

    def _load_prompt(self, filename: str) -> str:
        prompt_path = self._project_root / "prompts" / filename
        if not prompt_path.exists():
            raise LLMUnavailableError(f"Prompt file not found: {prompt_path}")
        return prompt_path.read_text(encoding="utf-8")

    def _init_client(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LLMUnavailableError("OPENAI_API_KEY is not set.")
        try:
            from openai import OpenAI
        except Exception as exc:  # pragma: no cover
            raise LLMUnavailableError(
                "openai package is not installed. Run: pip install openai"
            ) from exc
        self._client = OpenAI(api_key=api_key)

    def _chat_json(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt = self._load_prompt("mapping_system.txt")
        user_template = self._load_prompt("mapping_user.txt")
        payload_json = json.dumps(payload, ensure_ascii=False)
        user_prompt = user_template.replace("{payload_json}", payload_json)

        resp = self._client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        text = getattr(resp, "output_text", "")
        return _extract_json(text)

    def apply(self, plan: Dict[str, Any], feedback: List[str] | None = None) -> Dict[str, Any]:
        mapped = deepcopy(plan)
        payload = _to_prompt_payload(mapped, feedback=feedback)
        llm = self._chat_json(payload)

        group_items = llm.get("groups", []) or []
        row_items = llm.get("rows", []) or []

        group_by_key: Dict[tuple[int, str], Dict[str, Any]] = {}
        for item in group_items:
            key = (int(item.get("table_index", 0)), str(item.get("group_name", "")).strip())
            group_by_key[key] = item

        row_by_key: Dict[tuple[int, str, str], Dict[str, Any]] = {}
        for item in row_items:
            key = (
                int(item.get("table_index", 0)),
                str(item.get("group_name", "")).strip(),
                str(item.get("row_label", "")).strip(),
            )
            row_by_key[key] = item

        unresolved: List[str] = []
        for task in mapped.get("mapping_tasks", []):
            key = (int(task.get("table_index", 0)), str(task.get("group_name", "")).strip())
            item = group_by_key.get(key)
            if not item:
                unresolved.append(task.get("group_name", ""))
                continue
            task["group_type"] = str(item.get("group_type", "")).strip() or None
            task["candidate_csv_column"] = str(item.get("csv_column", "")).strip() or None
            raw_map = item.get("category_value_map", {}) or {}
            if isinstance(raw_map, dict):
                task["category_value_map"] = {
                    str(k): str(v) for k, v in raw_map.items() if str(k).strip() and str(v).strip()
                }
            else:
                task["category_value_map"] = {}
            task["confidence"] = float(item.get("confidence", 0.0) or 0.0)
            task["reason"] = str(item.get("reason", "")).strip()
            if not task["candidate_csv_column"]:
                unresolved.append(task.get("group_name", ""))

        for table in mapped.get("tables", []):
            table_index = int(table.get("table_index", 0))
            group_info = table.get("group_info", {})
            for group_name, info in group_info.items():
                item = group_by_key.get((table_index, str(group_name)))
                if item:
                    info["group_type"] = str(item.get("group_type", "")).strip() or None

            for row in table.get("ordered_rows", []):
                if str(row.get("kind")) != "data_row":
                    continue
                row_key = (
                    table_index,
                    str(row.get("group", "")).strip(),
                    str(row.get("label", "")).strip(),
                )
                row_item = row_by_key.get(row_key)
                if row_item:
                    row["format_hint"] = str(row_item.get("format_hint", "")).strip() or None

        mapped["unresolved"] = sorted(set(str(x) for x in unresolved if str(x).strip()))
        return mapped

    def generate_r_script(
        self,
        mapped_plan: Dict[str, Any],
        feedback: List[str] | None = None,
    ) -> Dict[str, Any]:
        """Generate executable R code from mapped plan using LLM."""
        payload = {"mapped_plan": mapped_plan, "feedback": feedback or []}
        system_prompt = self._load_prompt("codegen_system.txt")
        user_template = self._load_prompt("codegen_user.txt")
        payload_json = json.dumps(payload, ensure_ascii=False)
        user_prompt = user_template.replace("{payload_json}", payload_json)
        resp = self._client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        text = getattr(resp, "output_text", "")
        out = _extract_json(text)
        code = str(out.get("code", "") or "")
        warnings = [str(item) for item in list(out.get("warnings", []) or [])]
        return {"code": code, "warnings": warnings}
