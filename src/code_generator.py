"""Generate simple R table-summary code from a mapped analysis plan."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Dict, List


_STAT_TO_R_EXPR = {
    "count": "n = sum(!is.na(.data[[\"{var}\"]]))",
    "mean": "mean = ifelse(sum(!is.na(.data[[\"{var}\"]])) > 0, mean(.data[[\"{var}\"]], na.rm = TRUE), NA_real_)",
    "sd": "sd = ifelse(sum(!is.na(.data[[\"{var}\"]])) > 0, sd(.data[[\"{var}\"]], na.rm = TRUE), NA_real_)",
    "median": "median = ifelse(sum(!is.na(.data[[\"{var}\"]])) > 0, median(.data[[\"{var}\"]], na.rm = TRUE), NA_real_)",
    "min": "min = ifelse(sum(!is.na(.data[[\"{var}\"]])) > 0, min(.data[[\"{var}\"]], na.rm = TRUE), NA_real_)",
    "max": "max = ifelse(sum(!is.na(.data[[\"{var}\"]])) > 0, max(.data[[\"{var}\"]], na.rm = TRUE), NA_real_)",
}


@dataclass
class GenerationResult:
    code: str
    warnings: list[str]
    unsupported_statistics: list[dict]
    unresolved_dependencies: list[str]


def _r_string(text: str) -> str:
    escaped = str(text).replace("\\", "\\\\").replace("\"", "\\\"")
    return f"\"{escaped}\""


def _safe_object_name(prefix: str, section_name: str, suffix: str | None = None) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", section_name.lower()).strip("_")
    if not base:
        base = "section"
    object_name = f"{prefix}_{base}"
    if suffix:
        return f"{object_name}_{suffix}"
    return object_name


def _safe_suffix(text: Any) -> str:
    suffix = re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_")
    return suffix or "section"


def _section_suffix(section: Dict[str, Any], section_index: int) -> str:
    section_id = section.get("id")
    if section_id is not None and str(section_id).strip():
        return _safe_suffix(section_id)
    return str(section_index + 1)


def _unique_object_name(
    prefix: str,
    section: Dict[str, Any],
    section_index: int,
    used_names: set[str],
) -> str:
    name = str(section.get("name", "")).strip()
    base = _safe_object_name(prefix, name)
    if base not in used_names:
        used_names.add(base)
        return base

    candidate = _safe_object_name(prefix, name, _section_suffix(section, section_index))
    if candidate not in used_names:
        used_names.add(candidate)
        return candidate

    counter = 2
    while True:
        fallback = f"{candidate}_{counter}"
        if fallback not in used_names:
            used_names.add(fallback)
            return fallback
        counter += 1


def _comment_line(item: Any) -> str:
    if isinstance(item, dict):
        pairs = [f"{k}={v}" for k, v in item.items()]
        return ", ".join(pairs)
    return str(item)


def _add_unique(values: List[str], item: str) -> None:
    if item not in values:
        values.append(item)


def _continuous_block(
    section: Dict[str, Any],
    object_name: str,
    source_dataset: str | None,
    group_variable: str | None,
    warnings: List[str],
    unsupported_statistics: List[Dict[str, Any]],
    unresolved_dependencies: List[str],
) -> List[str]:
    name = str(section.get("name", "")).strip()
    variable = section.get("candidate_variable")
    stats = list(section.get("statistics", []) or [])

    lines: List[str] = []
    if not source_dataset:
        _add_unique(unresolved_dependencies, "plan.source_dataset")
        warnings.append(
            f"Missing dependency: plan.source_dataset for continuous section \"{name}\"."
        )
        lines.append(
            f"# TODO: set plan.source_dataset before generating grouped continuous section {_r_string(name)}"
        )
        return lines

    if not group_variable:
        _add_unique(unresolved_dependencies, "plan.group_variable")
        warnings.append(
            f"Missing dependency: plan.group_variable for continuous section \"{name}\"."
        )
        lines.append(
            f"# TODO: set plan.group_variable before generating grouped continuous section {_r_string(name)}"
        )
        return lines

    if not variable:
        _add_unique(
            unresolved_dependencies, f"continuous_sections.{name}.candidate_variable"
        )
        warnings.append(
            f"Missing dependency: candidate_variable for continuous section \"{name}\"."
        )
        lines.append(
            f"# TODO: map candidate_variable for continuous section {_r_string(name)}"
        )
        return lines

    if not stats:
        _add_unique(unresolved_dependencies, f"continuous_sections.{name}.statistics")
        warnings.append(
            f"Missing dependency: statistics for continuous section \"{name}\"."
        )
        lines.append(
            f"# TODO: add statistics for continuous section {_r_string(name)}"
        )
        return lines

    summary_parts = []
    unsupported = []
    for stat in stats:
        template = _STAT_TO_R_EXPR.get(stat)
        if template:
            summary_parts.append(template.format(var=variable))
        else:
            unsupported.append(stat)

    if unsupported:
        unsupported_statistics.append(
            {
                "section_type": "continuous",
                "section_name": name,
                "candidate_variable": variable,
                "statistics": unsupported,
            }
        )
        warnings.append(
            f"Unsupported statistics in continuous section \"{name}\": {', '.join(str(item) for item in unsupported)}."
        )
        lines.append(
            f"# TODO: unsupported statistics ignored for section {_r_string(name)}: {', '.join(str(item) for item in unsupported)}"
        )

    if not summary_parts:
        lines.append(
            f"# TODO: no supported statistics found for continuous section {_r_string(name)}"
        )
        return lines

    lines.append(f"# Continuous section: {name} -> {variable}")
    lines.append(f"{object_name} <- {source_dataset} %>%")
    lines.append(f"  group_by(.data[[\"{group_variable}\"]]) %>%")
    lines.append("  summarise(")
    for index, expr in enumerate(summary_parts):
        suffix = "," if index < len(summary_parts) - 1 else ""
        lines.append(f"    {expr}{suffix}")
    lines.append("  )")
    return lines


def _categorical_block(
    section: Dict[str, Any],
    object_name: str,
    source_dataset: str | None,
    group_variable: str | None,
    warnings: List[str],
    unresolved_dependencies: List[str],
) -> List[str]:
    name = str(section.get("name", "")).strip()
    variable = section.get("candidate_variable")
    categories = [str(item) for item in section.get("categories", []) or []]
    denominator_rule = section.get("denominator_rule")

    lines: List[str] = []
    if not source_dataset:
        _add_unique(unresolved_dependencies, "plan.source_dataset")
        warnings.append(
            f"Missing dependency: plan.source_dataset for categorical section \"{name}\"."
        )
        lines.append(
            f"# TODO: set plan.source_dataset before generating grouped categorical section {_r_string(name)}"
        )
        return lines

    if not group_variable:
        _add_unique(unresolved_dependencies, "plan.group_variable")
        warnings.append(
            f"Missing dependency: plan.group_variable for categorical section \"{name}\"."
        )
        lines.append(
            f"# TODO: set plan.group_variable before generating grouped categorical section {_r_string(name)}"
        )
        return lines

    if not variable:
        _add_unique(
            unresolved_dependencies, f"categorical_sections.{name}.candidate_variable"
        )
        warnings.append(
            f"Missing dependency: candidate_variable for categorical section \"{name}\"."
        )
        lines.append(
            f"# TODO: map candidate_variable for categorical section {_r_string(name)}"
        )
        return lines

    if not categories:
        _add_unique(unresolved_dependencies, f"categorical_sections.{name}.categories")
        warnings.append(
            f"Missing dependency: categories for categorical section \"{name}\"."
        )
        lines.append(
            f"# TODO: add category rows for categorical section {_r_string(name)}"
        )
        return lines

    if not denominator_rule:
        _add_unique(
            unresolved_dependencies, f"categorical_sections.{name}.denominator_rule"
        )
        warnings.append(
            f"Missing dependency: denominator_rule for categorical section \"{name}\"."
        )
        lines.append(
            f"# TODO: set denominator_rule for categorical section {_r_string(name)} (displayed_categories, nonmissing, group_total)"
        )
        return lines

    if denominator_rule not in {"displayed_categories", "nonmissing", "group_total"}:
        _add_unique(
            unresolved_dependencies, f"categorical_sections.{name}.denominator_rule"
        )
        warnings.append(
            f"Unsupported denominator_rule for categorical section \"{name}\": {denominator_rule}."
        )
        lines.append(
            f"# TODO: unsupported denominator_rule for categorical section {_r_string(name)}: {_r_string(str(denominator_rule))}"
        )
        return lines

    category_literal = ", ".join(_r_string(item) for item in categories)
    lines.append(f"# Categorical section: {name} -> {variable}")
    lines.append(f"# Denominator rule: {denominator_rule}")
    lines.append(f"{object_name} <- {source_dataset} %>%")
    lines.append(f"  filter(.data[[\"{variable}\"]] %in% c({category_literal})) %>%")
    lines.append(
        "  count(.data[[\"{0}\"]], .data[[\"{1}\"]], name = \"n\") %>%".format(
            group_variable, variable
        )
    )
    if denominator_rule == "displayed_categories":
        lines.append(f"  group_by(.data[[\"{group_variable}\"]]) %>%")
        lines.append("  mutate(percent = ifelse(sum(n) > 0, 100 * n / sum(n), NA_real_))")
        return lines

    denom_obj = f"{object_name}_denom"
    if denominator_rule == "nonmissing":
        lines.append("  ungroup()")
        lines.append(f"{denom_obj} <- {source_dataset} %>%")
        lines.append(f"  filter(!is.na(.data[[\"{variable}\"]])) %>%")
        lines.append(
            "  count(.data[[\"{0}\"]], name = \"denom_n\")".format(group_variable)
        )
        lines.append(f"{object_name} <- {object_name} %>%")
        lines.append(
            "  left_join({0}, by = c(\"{1}\")) %>%".format(denom_obj, group_variable)
        )
        lines.append("  mutate(percent = ifelse(denom_n > 0, 100 * n / denom_n, NA_real_)) %>%")
        lines.append("  select(-denom_n)")
        return lines

    lines.append("  ungroup()")
    lines.append(f"{denom_obj} <- {source_dataset} %>%")
    lines.append("  count(.data[[\"{0}\"]], name = \"denom_n\")".format(group_variable))
    lines.append(f"{object_name} <- {object_name} %>%")
    lines.append(
        "  left_join({0}, by = c(\"{1}\")) %>%".format(denom_obj, group_variable)
    )
    lines.append("  mutate(percent = ifelse(denom_n > 0, 100 * n / denom_n, NA_real_)) %>%")
    lines.append("  select(-denom_n)")
    return lines


def generate_r_code(plan: Dict[str, Any]) -> GenerationResult:
    """Generate R code for table summaries from a mapped analysis plan."""
    lines: List[str] = []
    warnings: List[str] = []
    unsupported_statistics: List[Dict[str, Any]] = []
    unresolved_dependencies: List[str] = []
    source_dataset = plan.get("source_dataset")
    group_variable = plan.get("group_variable")
    lines.append("# Auto-generated summary code")
    lines.append(
        "# Input data frame expected: "
        + (str(source_dataset) if source_dataset else "TODO plan.source_dataset")
    )
    lines.append("")

    assumptions = list(plan.get("assumptions", []) or [])
    lines.append("# Assumptions:")
    if assumptions:
        for item in assumptions:
            warnings.append(f"Assumption: {_comment_line(item)}")
            lines.append(f"# - {_comment_line(item)}")
    else:
        lines.append("# - none")
    lines.append("")

    unresolved = list(plan.get("unresolved_items", []) or [])
    lines.append("# Unresolved items:")
    if unresolved:
        for item in unresolved:
            warnings.append(f"Unresolved item: {_comment_line(item)}")
            lines.append(f"# - {_comment_line(item)}")
    else:
        lines.append("# - none")
    lines.append("")

    treatment_columns = list(plan.get("treatment_columns", []) or [])
    labels_literal = ", ".join(_r_string(item) for item in treatment_columns)
    lines.append("# Grouping context from the table shell")
    lines.append(f"treatment_columns <- c({labels_literal})")
    if not group_variable:
        _add_unique(unresolved_dependencies, "plan.group_variable")
        warnings.append("Missing dependency: plan.group_variable for grouped summaries.")
        lines.append(
            "# TODO: set plan.group_variable to enable grouped summary generation"
        )
    if not source_dataset:
        _add_unique(unresolved_dependencies, "plan.source_dataset")
        warnings.append("Missing dependency: plan.source_dataset for summary blocks.")
    lines.append("")

    lines.append("library(dplyr)")
    lines.append("")

    used_object_names: set[str] = set()

    for section_index, section in enumerate(plan.get("continuous_sections", []) or []):
        object_name = _unique_object_name(
            "continuous", section, section_index, used_object_names
        )
        lines.extend(
            _continuous_block(
                section,
                object_name,
                source_dataset,
                group_variable,
                warnings,
                unsupported_statistics,
                unresolved_dependencies,
            )
        )
        lines.append("")

    for section_index, section in enumerate(plan.get("categorical_sections", []) or []):
        object_name = _unique_object_name(
            "categorical", section, section_index, used_object_names
        )
        lines.extend(
            _categorical_block(
                section,
                object_name,
                source_dataset,
                group_variable,
                warnings,
                unresolved_dependencies,
            )
        )
        lines.append("")

    return GenerationResult(
        code="\n".join(lines).rstrip() + "\n",
        warnings=warnings,
        unsupported_statistics=unsupported_statistics,
        unresolved_dependencies=unresolved_dependencies,
    )
