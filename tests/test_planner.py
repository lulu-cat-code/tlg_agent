from src.planner import build_generation_plan


def test_build_generation_plan_creates_mapping_tasks_and_output_contract() -> None:
    parsed = {
        "docx_spec": {
            "source_file": "data/demo.docx",
            "document": {"title": "Demographics and Baseline Characteristics"},
            "table_shells": [
                {
                    "columns": ["Placebo", "Drug X"],
                    "group_sizes": {"Placebo": "10", "Drug X": "11"},
                    "ordered_rows": [
                        {"kind": "group_header", "label": "Age (yr)"},
                        {
                            "kind": "data_row",
                            "group": "Age (yr)",
                            "label": "Mean (SD)",
                            "format_hint": None,
                        },
                        {"kind": "group_header", "label": "Sex"},
                        {
                            "kind": "data_row",
                            "group": "Sex",
                            "label": "Male",
                            "format_hint": None,
                        },
                    ],
                    "row_groups": [
                        {"name": "Age (yr)", "subrows": ["Mean (SD)"]},
                        {"name": "Sex", "subrows": ["Male", "Female"]},
                    ],
                }
            ],
        },
        "csv_schema": {
            "csv_path": "data/adsl.csv",
            "dataset_name": "adsl",
            "columns": [{"name": "AGE"}, {"name": "SEX"}, {"name": "TRT01A"}],
        },
    }

    plan = build_generation_plan(parsed, trt_group_name="TRT01A")

    assert plan["title"] == "Demographics and Baseline Characteristics"
    assert plan["docx_source"] == "data/demo.docx"
    assert plan["csv_schema"]["dataset_name"] == "adsl"
    assert plan["trt_group_name"] == "TRT01A"
    assert plan["tables"] == [
        {
            "table_index": 1,
            "columns": ["Placebo", "Drug X"],
            "group_sizes": {"Placebo": "10", "Drug X": "11"},
            "ordered_rows": [
                {"kind": "group_header", "label": "Age (yr)"},
                {"kind": "data_row", "group": "Age (yr)", "label": "Mean (SD)", "format_hint": None},
                {"kind": "group_header", "label": "Sex"},
                {"kind": "data_row", "group": "Sex", "label": "Male", "format_hint": None},
            ],
            "group_info": {
                "Age (yr)": {"group_type": None, "subrows": ["Mean (SD)"]},
                "Sex": {"group_type": None, "subrows": ["Male", "Female"]},
            },
        }
    ]
    assert plan["mapping_tasks"] == [
        {
            "table_index": 1,
            "group_name": "Age (yr)",
            "group_slug": "age_yr",
            "group_type": None,
            "candidate_csv_column": None,
            "category_value_map": {},
            "confidence": 0.0,
            "reason": "",
        },
        {
            "table_index": 1,
            "group_name": "Sex",
            "group_slug": "sex",
            "group_type": None,
            "candidate_csv_column": None,
            "category_value_map": {},
            "confidence": 0.0,
            "reason": "",
        },
    ]
    assert plan["output_contract"] == {
        "preserve_docx_order": True,
        "preserve_docx_columns": True,
        "format_required": True,
    }
    assert plan["unresolved"] == []


def test_build_generation_plan_skips_empty_group_names() -> None:
    parsed = {
        "docx_spec": {
            "source_file": "data/demo.docx",
            "document": {"title": "Demo"},
            "table_shells": [
                {
                    "columns": ["Group A"],
                    "group_sizes": {},
                    "ordered_rows": [],
                    "row_groups": [
                        {"name": "", "subrows": ["ignore"]},
                        {"name": "Race", "subrows": ["Asian", "White"]},
                    ],
                }
            ],
        },
        "csv_schema": {"csv_path": "data/adsl.csv", "dataset_name": "adsl", "columns": []},
    }

    plan = build_generation_plan(parsed, trt_group_name="TRT01A")

    assert len(plan["mapping_tasks"]) == 1
    assert plan["mapping_tasks"][0]["group_name"] == "Race"
