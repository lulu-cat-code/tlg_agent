from src.planner import build_analysis_plan


def test_build_analysis_plan_classifies_sections_and_carries_parser_gaps() -> None:
    spec = {
        "source_file": "data/demo.docx",
        "document_structure": {
            "title": "Demographics and Baseline Characteristics",
            "population": None,
        },
        "table_shells": [
            {
                "columns": ["Placebo", "Drug X"],
                "row_groups": [
                    {
                        "name": "Age (yr)",
                        "subrows": ["n", "Mean (SD)", "Median", "Min\u2013max"],
                    },
                    {
                        "name": "Sex",
                        "subrows": ["Male", "Female"],
                    },
                ],
            }
        ],
        "summary_requirements": ["count", "mean", "sd", "median", "min", "max"],
        "warnings": ["Population is missing."],
        "missing_fields": ["population"],
        "clarification_questions": ["Population is missing. Should ITT Population be used?"],
        "proposed_assumptions": [{"field": "population", "value": "ITT Population"}],
    }

    plan = build_analysis_plan(spec)

    assert plan["table_title"] == "Demographics and Baseline Characteristics"
    assert plan["dataset_hint"] is None
    assert plan["treatment_columns"] == ["Placebo", "Drug X"]
    assert plan["requested_statistics"] == ["count", "mean", "sd", "median", "min", "max"]

    assert plan["continuous_sections"] == [
        {
            "name": "Age (yr)",
            "subrows": ["n", "Mean (SD)", "Median", "Min\u2013max"],
            "statistics": ["count", "mean", "sd", "median", "min", "max"],
            "candidate_variable": None,
        }
    ]
    assert plan["categorical_sections"] == [
        {
            "name": "Sex",
            "categories": ["Male", "Female"],
            "candidate_variable": None,
        }
    ]

    unresolved_types = {item["type"] for item in plan["unresolved_items"]}
    assert "warning" in unresolved_types
    assert "missing_population" in unresolved_types
    assert "clarification" in unresolved_types
    assert plan["assumptions"] == [{"field": "population", "value": "ITT Population"}]


def test_count_only_subrows_are_not_continuous_without_name_hint() -> None:
    spec = {
        "source_file": "data/demo.docx",
        "document_structure": {"title": "Count Only Table", "population": "Safety Population"},
        "table_shells": [
            {
                "columns": ["Group A"],
                "row_groups": [{"name": "Screened subjects", "subrows": ["n"]}],
            }
        ],
        "summary_requirements": ["count"],
        "warnings": [],
        "missing_fields": [],
        "clarification_questions": [],
        "proposed_assumptions": [],
    }

    plan = build_analysis_plan(spec)

    assert plan["continuous_sections"] == []
    assert plan["categorical_sections"] == []
    assert any(item["type"] == "classification" for item in plan["unresolved_items"])
