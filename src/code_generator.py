"""LLM-based R code generator with unresolved-mapping tracking."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List

from src.llm_agent import LLMDecisionEngine


@dataclass
class GenerationResult:
    code: str
    warnings: list[str]
    unresolved_mappings: list[str]
    unsupported_statistics: list[dict[str, Any]] | None = None
    unresolved_dependencies: list[str] | None = None


def _collect_unresolved(plan: Dict[str, Any]) -> list[str]:
    unresolved = set(str(x) for x in list(plan.get("unresolved", []) or []) if str(x).strip())
    for task in plan.get("mapping_tasks", []) or []:
        if not str(task.get("candidate_csv_column", "")).strip():
            unresolved.add(str(task.get("group_name", "")).strip())
    return sorted(x for x in unresolved if x)


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(text or "").lower()).strip("_")
    return slug or "section"


def _unique_object_name(prefix: str, name: str, used: dict[str, int], section_id: str | None = None) -> str:
    base = f"{prefix}_{_slugify(name)}"
    count = used.get(base, 0) + 1
    used[base] = count
    if count == 1:
        return base
    if section_id:
        return f"{base}_{_slugify(section_id)}"
    return f"{base}_{count}"


def _build_legacy_r_code(plan: Dict[str, Any]) -> GenerationResult:
    warnings: List[str] = []
    unresolved_dependencies: List[str] = []
    unsupported_statistics: List[Dict[str, Any]] = []
    lines: List[str] = [
        "library(dplyr)",
        "",
        "# Assumptions:",
    ]

    assumptions = list(plan.get("assumptions", []) or [])
    if assumptions:
        for item in assumptions:
            field = item.get("field")
            value = item.get("value")
            lines.append(f"# - field={field}, value={value}")
            warnings.append(f"Assumption: field={field}, value={value}")
    else:
        lines.append("# - none")

    lines.extend(["", "# Unresolved items:"])
    unresolved_items = list(plan.get("unresolved_items", []) or [])
    if unresolved_items:
        for item in unresolved_items:
            item_type = item.get("type")
            message = item.get("message")
            lines.append(f"# - type={item_type}, message={message}")
            warnings.append(f"Unresolved item: type={item_type}, message={message}")
    else:
        lines.append("# - none")

    treatment_columns = plan.get("treatment_columns", []) or []
    lines.extend(["", f'treatment_columns <- c({", ".join(repr(str(x)).replace("\'", "\"") for x in treatment_columns)})'])

    source_dataset = plan.get("source_dataset")
    group_variable = plan.get("group_variable")
    if not group_variable:
        warnings.append("Missing dependency: plan.group_variable for grouped summaries.")
        unresolved_dependencies.append("plan.group_variable")
        lines.append("# TODO: set plan.group_variable to enable grouped summary generation")
    if not source_dataset:
        warnings.append("Missing dependency: plan.source_dataset for summary blocks.")
        unresolved_dependencies.append("plan.source_dataset")

    used_names: Dict[str, int] = {}
    supported_stats = {"count", "mean", "sd", "median", "min", "max"}

    for section in plan.get("continuous_sections", []) or []:
        name = str(section.get("name", ""))
        candidate_variable = section.get("candidate_variable")
        statistics = list(section.get("statistics", []) or [])
        if not candidate_variable:
            unresolved_dependencies.append(f"continuous_sections.{name}.candidate_variable")
            lines.append(f'# TODO: map candidate_variable for continuous section "{name}"')
            continue
        if not source_dataset:
            lines.append(f'# TODO: set plan.source_dataset before generating grouped continuous section "{name}"')
            continue
        if not group_variable:
            continue

        unsupported = [stat for stat in statistics if stat not in supported_stats]
        if unsupported:
            unsupported_statistics.append(
                {
                    "section_type": "continuous",
                    "section_name": name,
                    "candidate_variable": candidate_variable,
                    "statistics": unsupported,
                }
            )
            lines.append(f'# TODO: unsupported statistics ignored for section "{name}": {", ".join(unsupported)}')

        object_name = _unique_object_name("continuous", name, used_names, section.get("id"))
        lines.append(f"{object_name} <- {source_dataset} %>%")
        lines.append(f'  group_by(.data[["{group_variable}"]]) %>%')
        summary_parts: List[str] = []
        if "count" in statistics:
            summary_parts.append('n = sum(!is.na(.data[["%s"]]))' % candidate_variable)
        if "mean" in statistics:
            summary_parts.append('mean = ifelse(sum(!is.na(.data[["%s"]])) > 0, mean(.data[["%s"]], na.rm = TRUE), NA_real_)' % (candidate_variable, candidate_variable))
        if "sd" in statistics:
            summary_parts.append('sd = ifelse(sum(!is.na(.data[["%s"]])) > 1, sd(.data[["%s"]], na.rm = TRUE), NA_real_)' % (candidate_variable, candidate_variable))
        if "median" in statistics:
            summary_parts.append('median = ifelse(sum(!is.na(.data[["%s"]])) > 0, median(.data[["%s"]], na.rm = TRUE), NA_real_)' % (candidate_variable, candidate_variable))
        if "min" in statistics:
            summary_parts.append('min = ifelse(sum(!is.na(.data[["%s"]])) > 0, min(.data[["%s"]], na.rm = TRUE), NA_real_)' % (candidate_variable, candidate_variable))
        if "max" in statistics:
            summary_parts.append('max = ifelse(sum(!is.na(.data[["%s"]])) > 0, max(.data[["%s"]], na.rm = TRUE), NA_real_)' % (candidate_variable, candidate_variable))
        if summary_parts:
            lines.append(f'  summarise({", ".join(summary_parts)}, .groups = "drop")')
        lines.append("")

    for section in plan.get("categorical_sections", []) or []:
        name = str(section.get("name", ""))
        candidate_variable = section.get("candidate_variable")
        denominator_rule = section.get("denominator_rule")
        categories = list(section.get("categories", []) or [])
        if not candidate_variable:
            unresolved_dependencies.append(f"categorical_sections.{name}.candidate_variable")
            lines.append(f'# TODO: map candidate_variable for categorical section "{name}"')
            continue
        if not denominator_rule:
            unresolved_dependencies.append(f"categorical_sections.{name}.denominator_rule")
            lines.append(f'# TODO: set denominator_rule for categorical section "{name}" (displayed_categories, nonmissing, group_total)')
            continue
        if not source_dataset:
            lines.append(f'# TODO: set plan.source_dataset before generating grouped categorical section "{name}"')
            continue
        if not group_variable:
            continue

        object_name = _unique_object_name("categorical", name, used_names)
        lines.append(f"# Denominator rule: {denominator_rule}")
        if denominator_rule == "displayed_categories":
            category_list = ", ".join(repr(str(x)).replace("\'", "\"") for x in categories)
            lines.append(f"{object_name} <- {source_dataset} %>%")
            lines.append(f'  filter(.data[["{candidate_variable}"]] %in% c({category_list})) %>%')
            lines.append(f'  count(.data[["{group_variable}"]], .data[["{candidate_variable}"]], name = "n") %>%')
            lines.append(f'  group_by(.data[["{group_variable}"]]) %>%')
            lines.append('  mutate(percent = ifelse(sum(n) > 0, 100 * n / sum(n), NA_real_))')
        elif denominator_rule in {"nonmissing", "group_total"}:
            lines.append(f"{object_name}_denom <- {source_dataset} %>%")
            if denominator_rule == "nonmissing":
                lines.append(f'  filter(!is.na(.data[["{candidate_variable}"]])) %>%')
            lines.append(f'  count(.data[["{group_variable}"]], name = "denom_n")')
            category_list = ", ".join(repr(str(x)).replace("\'", "\"") for x in categories)
            lines.append(f"{object_name} <- {source_dataset} %>%")
            lines.append(f'  filter(.data[["{candidate_variable}"]] %in% c({category_list})) %>%')
            lines.append(f'  count(.data[["{group_variable}"]], .data[["{candidate_variable}"]], name = "n") %>%')
            lines.append(f'  left_join({object_name}_denom, by = c("{group_variable}")) %>%')
            lines.append('  mutate(percent = ifelse(denom_n > 0, 100 * n / denom_n, NA_real_)) %>%')
            lines.append("  ungroup()")
        lines.append("")

    return GenerationResult(
        code="\n".join(lines).rstrip() + "\n",
        warnings=warnings,
        unresolved_mappings=[],
        unsupported_statistics=unsupported_statistics,
        unresolved_dependencies=sorted(set(unresolved_dependencies)),
    )


def generate_r_code(
    plan: Dict[str, Any],
    llm_engine: LLMDecisionEngine | None = None,
    feedback: List[str] | None = None,
) -> GenerationResult:
    """Generate executable R script via LLM from mapped plan."""
    if llm_engine is None:
        return _build_legacy_r_code(plan)

    payload = llm_engine.generate_r_script(mapped_plan=plan, feedback=feedback)
    code = str(payload.get("code", "") or "")
    warnings = [str(item) for item in list(payload.get("warnings", []) or [])]
    unresolved = _collect_unresolved(plan)
    return GenerationResult(
        code=code,
        warnings=warnings,
        unresolved_mappings=unresolved,
        unsupported_statistics=[],
        unresolved_dependencies=[],
    )
