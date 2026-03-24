"""Layered DOCX parser: extraction, normalization, and interpretation."""

from pathlib import Path
from typing import Any, Dict, List
import xml.etree.ElementTree as ET
import re
import zipfile

from docx import Document


def _extract_tables(document: Document) -> List[List[List[str]]]:
    """Layer 1 helper: extract raw table cells as list[table][row][cell]."""
    tables: List[List[List[str]]] = []
    for table in document.tables:
        rows: List[List[str]] = []
        for row in table.rows:
            rows.append([cell.text for cell in row.cells])
        tables.append(rows)
    return tables


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _normalize_row_label(label: str) -> str:
    normalized = _normalize_whitespace(label)
    if re.fullmatch(r"min\s*[-–—]?\s*max", normalized, flags=re.IGNORECASE):
        return "Min–max"
    return normalized


def _extract_footnotes_from_xml(xml_blob: bytes) -> List[str]:
    """Extract footnotes text from footnotes.xml/endnotes.xml content."""
    root = ET.fromstring(xml_blob)
    footnotes: List[str] = []
    for footnote in root.iter():
        if not footnote.tag.endswith("footnote") and not footnote.tag.endswith("endnote"):
            continue

        note_type = ""
        for attr_key, attr_val in footnote.attrib.items():
            if attr_key.endswith("}type"):
                note_type = attr_val
                break
        if note_type in {"separator", "continuationSeparator", "continuationNotice"}:
            continue

        parts: List[str] = []
        for node in footnote.iter():
            if not node.tag.endswith("t"):
                continue
            if node.text:
                parts.append(node.text)
        text = _normalize_whitespace("".join(parts))
        if text:
            footnotes.append(text)
    return footnotes


def _extract_footnotes(file_path: Path) -> List[str]:
    """Layer 1 helper: extract footnotes/endnotes directly from DOCX package."""
    note_files = ["word/footnotes.xml", "word/endnotes.xml"]
    extracted: List[str] = []
    try:
        with zipfile.ZipFile(file_path) as archive:
            for note_file in note_files:
                try:
                    xml_blob = archive.read(note_file)
                except KeyError:
                    continue
                extracted.extend(_extract_footnotes_from_xml(xml_blob))
    except FileNotFoundError:
        return []
    return extracted


def extract_raw_docx(filename: str, data_dir: str = "data") -> Dict[str, Any]:
    """Layer 1: read DOCX and return raw extracted content."""
    file_path = Path(data_dir) / filename
    document = Document(file_path)
    return {
        "source_file": str(file_path),
        "paragraphs": [p.text for p in document.paragraphs],
        "tables": _extract_tables(document),
        "footnotes": _extract_footnotes(file_path),
    }


def normalize_extracted_content(raw_content: Dict[str, Any]) -> Dict[str, Any]:
    """Layer 2: normalize whitespace and clean extracted paragraphs/tables."""
    paragraphs = [p.strip() for p in raw_content.get("paragraphs", []) if p and p.strip()]

    normalized_tables: List[List[List[str]]] = []
    for table in raw_content.get("tables", []):
        rows: List[List[str]] = []
        for row in table:
            rows.append([str(cell).strip() for cell in row])
        if rows:
            normalized_tables.append(rows)

    footnotes = [f.strip() for f in raw_content.get("footnotes", []) if f and f.strip()]

    return {
        "source_file": raw_content.get("source_file", ""),
        "paragraphs": paragraphs,
        "tables": normalized_tables,
        "footnotes": footnotes,
    }


def _is_section_header(paragraph: str) -> bool:
    if paragraph.endswith(":"):
        return True
    words = paragraph.split()
    if not words or len(words) > 8:
        return False
    titled = sum(1 for w in words if w[:1].isupper())
    return titled >= max(1, len(words) - 1)


def _clean_subrow_label(label: str) -> str:
    return _normalize_row_label(re.sub(r"^[\-\*]\s*", "", label))


def _preserve_category_label(label: str, group_name: str) -> str:
    """
    Preserve category intent when possible.
    Example: for age-group buckets, "65" is normalized to "≥65".
    """
    normalized_label = _clean_subrow_label(label)
    group = group_name.lower()
    if "age group" in group and re.fullmatch(r"\d+", normalized_label):
        return f"≥{normalized_label}"
    if normalized_label.startswith(">="):
        return "≥" + normalized_label[2:].strip()
    return normalized_label


def _to_table_shell(table: List[List[str]]) -> Dict[str, Any]:
    if not table:
        return {
            "columns": [],
            "group_sizes": {},
            "rows": [],
            "row_groups": [],
        }

    raw_columns = table[0]
    # First column is row labels; ignore it for treatment-group columns.
    group_columns = raw_columns[1:] if len(raw_columns) > 1 else []
    columns: List[str] = []
    group_sizes: Dict[str, str] = {}
    for raw in group_columns:
        header = raw.strip()
        if not header:
            continue
        match = re.match(
            r"^(.*?)\s*\(\s*N\s*=\s*([^)]+)\s*\)\s*$",
            header,
            flags=re.IGNORECASE | re.DOTALL,
        )
        if match:
            group_name = match.group(1).strip()
            group_n = match.group(2).strip()
        else:
            group_name = header.splitlines()[0].strip()
            group_n = ""
        if not group_name:
            continue
        columns.append(group_name)
        if group_n:
            group_sizes[group_name] = group_n

    rows: List[Dict[str, str]] = []
    row_groups: List[Dict[str, Any]] = []
    current_group: Dict[str, Any] | None = None
    for row in table[1:]:
        first_cell = _normalize_row_label(row[0]) if row else ""
        values = [row[idx].strip() if idx < len(row) else "" for idx in range(1, len(columns) + 1)]
        if not first_cell:
            continue

        # Row group header: label present, all treatment values empty.
        if all(not value for value in values):
            current_group = {"name": first_cell, "subrows": []}
            row_groups.append(current_group)
            continue

        # Subrow/data row: label present, at least one treatment value present.
        if current_group is not None:
            current_group["subrows"].append(
                _preserve_category_label(first_cell, current_group["name"])
            )

        row_label = first_cell
        if current_group is not None:
            row_label = _preserve_category_label(first_cell, current_group["name"])

        row_dict: Dict[str, str] = {"row_label": row_label}
        for idx, column in enumerate(columns, start=1):
            value = row[idx] if idx < len(row) else ""
            row_dict[column] = value
        rows.append(row_dict)

    return {
        "columns": columns,
        "group_sizes": group_sizes,
        "rows": rows,
        "row_groups": row_groups,
    }


def _extract_population(paragraphs: List[str], footnotes: List[str]) -> Any:
    """Return a population-like statement, or None when missing/placeholder."""
    for text in paragraphs + footnotes:
        if "population" in text.lower():
            if "<specify population>" in text.lower():
                return None
            return text
    return None


def detect_summary_statistics(rows: List[Dict[str, Any]]) -> List[str]:
    """Detect summary statistics from row labels."""
    found = {
        "count": False,
        "mean": False,
        "sd": False,
        "median": False,
        "min": False,
        "max": False,
    }

    for row in rows:
        label = str(row.get("row_label", "")).strip().lower()
        if not label:
            continue
        normalized = label.replace("–", "-").replace("—", "-")

        if normalized == "n" or " n " in f" {normalized} ":
            found["count"] = True
        if "mean" in normalized:
            found["mean"] = True
        if "sd" in normalized:
            found["sd"] = True
        if "mean (sd)" in normalized or "mean(sd)" in normalized:
            found["mean"] = True
            found["sd"] = True
        if "median" in normalized:
            found["median"] = True
        if "min-max" in normalized or "minmax" in normalized:
            found["min"] = True
            found["max"] = True
        if "range" in normalized:
            found["min"] = True
            found["max"] = True

    ordered_stats = ["count", "mean", "sd", "median", "min", "max"]
    return [stat for stat in ordered_stats if found[stat]]


def _validate_required_fields(spec: Dict[str, Any]) -> Dict[str, Any]:
    """Validate required fields and enrich spec with gaps/questions/assumptions."""
    missing_fields: List[str] = []
    clarification_questions: List[str] = []
    proposed_assumptions: List[Dict[str, str]] = []
    warnings = spec.get("warnings", [])

    title = spec["document_structure"].get("title", "")
    population = spec["document_structure"].get("population")
    table_shells = spec.get("table_shells", [])

    has_columns = any(shell.get("columns") for shell in table_shells)
    has_row_groups = any(shell.get("row_groups") for shell in table_shells)

    if not title:
        missing_fields.append("title")
    if not population:
        missing_fields.append("population")
        warnings.append("Population is missing.")
        clarification_questions.append(
            "Population is missing. Should ITT Population be used?"
        )
        proposed_assumptions.append(
            {"field": "population", "value": "ITT Population"}
        )
    if not has_columns:
        missing_fields.append("columns")
    if not has_row_groups:
        missing_fields.append("row groups")

    spec["missing_fields"] = missing_fields
    spec["clarification_questions"] = clarification_questions
    spec["proposed_assumptions"] = proposed_assumptions
    spec["warnings"] = warnings
    return spec


def interpret_parser_spec(normalized_content: Dict[str, Any]) -> Dict[str, Any]:
    """Layer 3: interpret normalized content into parser specification."""
    paragraphs = normalized_content.get("paragraphs", [])
    tables = normalized_content.get("tables", [])
    footnotes = normalized_content.get("footnotes", [])

    title = paragraphs[0] if paragraphs else ""
    section_headers = [p for p in paragraphs if _is_section_header(p)]
    if title:
        section_headers = [header for header in section_headers if header != title]
    table_shells = [_to_table_shell(table) for table in tables]
    population = _extract_population(paragraphs, footnotes)

    summary_rows: List[Dict[str, Any]] = []
    for shell in table_shells:
        for row in shell.get("rows", []):
            summary_rows.append({"row_label": row.get("row_label", "")})
    summary_requirements = detect_summary_statistics(summary_rows)
    format_requirements = [
        p
        for p in paragraphs
        if "format" in p.lower()
        or "template" in p.lower()
        or "structure" in p.lower()
    ]

    warnings: List[str] = []
    if not title:
        warnings.append("No title detected from paragraphs.")
    if not table_shells:
        warnings.append("No tables detected in document.")

    spec = {
        "document_structure": {
            "title": title,
            "section_headers": section_headers,
            "footnotes": footnotes,
            "population": population,
        },
        "table_shells": table_shells,
        "summary_requirements": summary_requirements,
        "format_requirements": format_requirements,
        "warnings": warnings,
    }
    return _validate_required_fields(spec)


def parse_docx_to_spec(filename: str, data_dir: str = "data") -> Dict[str, Any]:
    """Convenience function chaining all 3 layers."""
    raw_content = extract_raw_docx(filename=filename, data_dir=data_dir)
    normalized_content = normalize_extracted_content(raw_content)
    return interpret_parser_spec(normalized_content)


def extract_docx_content(filename: str, data_dir: str = "data") -> Dict[str, Any]:
    """
    Backward-compatible API name.
    Returns the interpreted parser specification.
    """
    return parse_docx_to_spec(filename=filename, data_dir=data_dir)
