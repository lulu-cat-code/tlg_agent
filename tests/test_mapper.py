from src.mapper import map_candidate_variables


def test_map_candidate_variables_fills_known_demographic_sections() -> None:
    plan = {
        "table_title": "Demographics and Baseline Characteristics Table",
        "dataset_hint": None,
        "treatment_columns": ["Group 1", "Group 2"],
        "continuous_sections": [
            {
                "name": "Age (yr)",
                "subrows": ["n", "Mean (SD)", "Median", "Min-max"],
                "statistics": ["count", "mean", "sd", "median", "min", "max"],
                "candidate_variable": None,
            },
            {
                "name": "Weight (kg) at (timepoint)",
                "subrows": ["n", "Mean (SD)", "Median"],
                "statistics": ["count", "mean", "sd", "median"],
                "candidate_variable": None,
            },
        ],
        "categorical_sections": [
            {"name": "Sex", "categories": ["Male", "Female"], "candidate_variable": None},
            {"name": "Ethnicity", "categories": ["Hispanic", "Not Hispanic"], "candidate_variable": None},
            {"name": "Race", "categories": ["Asian", "White"], "candidate_variable": None},
            {"name": "Age group (yr)", "categories": ["18-40", "41-64", "65+"], "candidate_variable": None},
        ],
        "requested_statistics": ["count", "mean", "sd", "median", "min", "max"],
        "unresolved_items": [{"type": "warning", "message": "Population is missing."}],
        "assumptions": [{"field": "population", "value": "ITT Population"}],
    }

    mapped = map_candidate_variables(plan)

    assert mapped["continuous_sections"][0]["candidate_variable"] == "AGE"
    assert mapped["continuous_sections"][1]["candidate_variable"] == "WEIGHT"
    assert mapped["categorical_sections"][0]["candidate_variable"] == "SEX"
    assert mapped["categorical_sections"][1]["candidate_variable"] == "ETHNIC"
    assert mapped["categorical_sections"][2]["candidate_variable"] == "RACE"
    assert mapped["categorical_sections"][3]["candidate_variable"] == "AGEGR1"

    assert mapped["unresolved_items"] == plan["unresolved_items"]
    assert mapped["assumptions"] == plan["assumptions"]


def test_map_candidate_variables_keeps_unmapped_as_none() -> None:
    plan = {
        "table_title": "Other Table",
        "dataset_hint": None,
        "treatment_columns": ["Group 1"],
        "continuous_sections": [
            {
                "name": "Height (cm)",
                "subrows": ["n", "Mean (SD)"],
                "statistics": ["count", "mean", "sd"],
                "candidate_variable": None,
            }
        ],
        "categorical_sections": [
            {"name": "Smoking status", "categories": ["Yes", "No"], "candidate_variable": None}
        ],
        "requested_statistics": ["count", "mean", "sd"],
        "unresolved_items": [],
        "assumptions": [],
    }

    mapped = map_candidate_variables(plan)

    assert mapped["continuous_sections"][0]["candidate_variable"] is None
    assert mapped["categorical_sections"][0]["candidate_variable"] is None
