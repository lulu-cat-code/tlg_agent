from pathlib import Path

from docx import Document

from src.parser import (
    _extract_footnotes_from_xml,
    detect_summary_statistics,
    extract_raw_docx,
    normalize_extracted_content,
    interpret_parser_spec,
    parse_docx_to_spec,
)


def test_parse_docx_to_spec_returns_expected_top_level_keys(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "sample.docx"

    doc = Document()
    doc.add_paragraph("TLG Shell Title")
    doc.add_paragraph("Section One:")
    doc.add_paragraph("Population: Safety Population")
    doc.add_paragraph("Output format: JSON")
    table = doc.add_table(rows=9, cols=2)
    table.cell(0, 0).text = "Field"
    table.cell(0, 1).text = "Value"
    table.cell(1, 0).text = "Age (yr)"
    table.cell(1, 1).text = ""
    table.cell(2, 0).text = "n"
    table.cell(2, 1).text = "100"
    table.cell(3, 0).text = "Mean (SD)"
    table.cell(3, 1).text = "12.3 (1.1)"
    table.cell(4, 0).text = "Median"
    table.cell(4, 1).text = "12.1"
    table.cell(5, 0).text = "Min-max"
    table.cell(5, 1).text = "10.0-15.0"
    table.cell(6, 0).text = "Sex"
    table.cell(6, 1).text = ""
    table.cell(7, 0).text = "Male"
    table.cell(7, 1).text = "60 (60%)"
    table.cell(8, 0).text = "Female"
    table.cell(8, 1).text = "40 (40%)"
    doc.save(file_path)

    result = parse_docx_to_spec("sample.docx", data_dir=str(data_dir))

    assert "document_structure" in result
    assert "table_shells" in result
    assert "summary_requirements" in result
    assert "format_requirements" in result
    assert "warnings" in result
    assert "missing_fields" in result
    assert "clarification_questions" in result
    assert "proposed_assumptions" in result

    assert result["document_structure"]["title"] == "TLG Shell Title"
    assert "Section One:" in result["document_structure"]["section_headers"]
    assert isinstance(result["document_structure"]["footnotes"], list)
    assert result["document_structure"]["population"] == "Population: Safety Population"

    assert result["table_shells"][0]["columns"] == ["Value"]
    assert result["table_shells"][0]["group_sizes"] == {}
    assert result["table_shells"][0]["rows"] == [
        {"row_label": "n", "Value": "100"},
        {"row_label": "Mean (SD)", "Value": "12.3 (1.1)"},
        {"row_label": "Median", "Value": "12.1"},
        {"row_label": "Min–max", "Value": "10.0-15.0"},
        {"row_label": "Male", "Value": "60 (60%)"},
        {"row_label": "Female", "Value": "40 (40%)"},
    ]
    assert result["table_shells"][0]["row_groups"] == [
        {"name": "Age (yr)", "subrows": ["n", "Mean (SD)", "Median", "Min–max"]},
        {"name": "Sex", "subrows": ["Male", "Female"]},
    ]

    assert result["summary_requirements"] == [
        "count",
        "mean",
        "sd",
        "median",
        "min",
        "max",
    ]
    assert any("format" in item.lower() for item in result["format_requirements"])
    assert result["warnings"] == []
    assert result["missing_fields"] == []
    assert result["clarification_questions"] == []
    assert result["proposed_assumptions"] == []


def test_layer_functions_are_individually_testable(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    file_path = data_dir / "layered.docx"

    doc = Document()
    doc.add_paragraph("  Title  ")
    doc.add_paragraph("  ")
    table = doc.add_table(rows=3, cols=2)
    table.cell(0, 0).text = "Col1"
    table.cell(0, 1).text = "Col2"
    table.cell(1, 0).text = "Section A"
    table.cell(1, 1).text = ""
    table.cell(2, 0).text = "- detail"
    table.cell(2, 1).text = "note"
    doc.save(file_path)

    raw = extract_raw_docx("layered.docx", data_dir=str(data_dir))
    assert raw["source_file"] == str(file_path)
    assert raw["paragraphs"][0] == "  Title  "

    normalized = normalize_extracted_content(raw)
    assert normalized["paragraphs"] == ["Title"]

    spec = interpret_parser_spec(normalized)
    assert spec["document_structure"]["title"] == "Title"
    assert spec["table_shells"][0]["columns"] == ["Col2"]
    assert spec["table_shells"][0]["group_sizes"] == {}
    assert spec["table_shells"][0]["rows"] == [{"row_label": "detail", "Col2": "note"}]
    assert spec["table_shells"][0]["row_groups"] == [
        {"name": "Section A", "subrows": ["detail"]}
    ]
    assert spec["missing_fields"] == ["population"]
    assert "Population is missing." in spec["warnings"]
    assert spec["clarification_questions"] == [
        "Population is missing. Should ITT Population be used?"
    ]
    assert spec["proposed_assumptions"] == [
        {"field": "population", "value": "ITT Population"}
    ]


def test_tlg_shell_t1_footnotes_present_population_missing() -> None:
    normalized = {
        "source_file": "TLG_shell_t1.docx",
        "paragraphs": ["TLG Shell T1", "Section A:", "Output format: RTF"],
        "tables": [[["Column A", "Column B"], ["- age 65+", "subgroup"]]],
        "footnotes": ["Footnote 1: Use standard coding dictionary."],
    }

    spec = interpret_parser_spec(normalized)

    assert spec["document_structure"]["footnotes"] == [
        "Footnote 1: Use standard coding dictionary."
    ]
    assert spec["document_structure"]["population"] is None
    assert "population" in spec["missing_fields"]
    assert "Population is missing." in spec["warnings"]
    assert spec["clarification_questions"] == [
        "Population is missing. Should ITT Population be used?"
    ]
    assert spec["proposed_assumptions"] == [
        {"field": "population", "value": "ITT Population"}
    ]


def test_specify_population_placeholder_treated_as_missing() -> None:
    normalized = {
        "source_file": "TLG_shell_t1.docx",
        "paragraphs": [
            "Demographics and Baseline Characteristics Table",
            "Demographics and Baseline Characteristics: <Specify Population>\nProtocol: xxnnnn",
        ],
        "tables": [[["Column A", "Column B"], ["- age 65+", "subgroup"]]],
        "footnotes": ["Footnote: baseline definitions."],
    }

    spec = interpret_parser_spec(normalized)

    assert spec["document_structure"]["population"] is None
    assert "population" in spec["missing_fields"]
    assert "Population is missing." in spec["warnings"]
    assert spec["clarification_questions"] == [
        "Population is missing. Should ITT Population be used?"
    ]
    assert spec["proposed_assumptions"] == [
        {"field": "population", "value": "ITT Population"}
    ]


def test_group_columns_and_sample_sizes_are_extracted_cleanly() -> None:
    normalized = {
        "source_file": "TLG_shell_t1.docx",
        "paragraphs": ["Demographics table", "Population: Safety Population"],
        "tables": [
            [
                ["", "Group 1\n(N=nnn)", "Group 2\n(N=nnn)", "Group 3\n(N=nnn)"],
                ["Age (yr)", "", "", ""],
                ["n", "xx", "yy", "zz"],
                ["- 18-40", "a", "b", "c"],
            ]
        ],
        "footnotes": [],
    }

    spec = interpret_parser_spec(normalized)
    shell = spec["table_shells"][0]

    assert shell["columns"] == ["Group 1", "Group 2", "Group 3"]
    assert shell["group_sizes"] == {
        "Group 1": "nnn",
        "Group 2": "nnn",
        "Group 3": "nnn",
    }
    assert shell["rows"] == [
        {"row_label": "n", "Group 1": "xx", "Group 2": "yy", "Group 3": "zz"},
        {"row_label": "18-40", "Group 1": "a", "Group 2": "b", "Group 3": "c"},
    ]
    assert shell["row_groups"] == [{"name": "Age (yr)", "subrows": ["n", "18-40"]}]


def test_detect_summary_statistics_from_row_labels() -> None:
    rows = [
        {"row_label": "n"},
        {"row_label": "Mean (SD)"},
        {"row_label": "Median"},
        {"row_label": "Min–max"},
    ]
    assert detect_summary_statistics(rows) == [
        "count",
        "mean",
        "sd",
        "median",
        "min",
        "max",
    ]


def test_row_label_normalization_for_newlines_and_symbols() -> None:
    normalized = {
        "source_file": "TLG_shell_t1.docx",
        "paragraphs": ["Demo Table", "Population: Safety Population"],
        "tables": [
            [
                ["", "Group 1\n(N=10)"],
                ["Age group (yr)", ""],
                ["≥65", "3"],
                ["65", "2"],
                ["Minmax", "1-9"],
                ["Race", ""],
                ["Native Hawaiian or \nother Pacific Islander", "2"],
            ]
        ],
        "footnotes": [],
    }

    spec = interpret_parser_spec(normalized)
    shell = spec["table_shells"][0]
    labels = [row["row_label"] for row in shell["rows"]]

    assert "≥65" in labels
    assert labels.count("≥65") >= 2
    assert "Min–max" in labels
    assert "Native Hawaiian or other Pacific Islander" in labels


def test_extract_footnotes_from_xml_blob() -> None:
    xml_blob = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:footnotes xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:footnote w:id="-1" w:type="separator"><w:p><w:r><w:t>---</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="1"><w:p><w:r><w:t>First note</w:t></w:r></w:p></w:footnote>
  <w:footnote w:id="2"><w:p><w:r><w:t>Second</w:t></w:r><w:r><w:t> note</w:t></w:r></w:p></w:footnote>
</w:footnotes>
"""
    assert _extract_footnotes_from_xml(xml_blob) == ["First note", "Second note"]
