from src.code_generator import GenerationResult, generate_r_code


def test_generate_r_code_includes_comments_grouping_and_summaries() -> None:
    plan = {
        "table_title": "Demographics and Baseline Characteristics Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": ["Group 1", "Group 2", "Group 3"],
        "continuous_sections": [
            {
                "name": "Age (yr)",
                "subrows": ["n", "Mean (SD)", "Median", "Min-max"],
                "statistics": ["count", "mean", "sd", "median", "min", "max"],
                "candidate_variable": "AGE",
            },
            {
                "name": "Height (cm)",
                "subrows": ["n", "Mean (SD)"],
                "statistics": ["count", "mean", "sd"],
                "candidate_variable": None,
            },
        ],
        "categorical_sections": [
            {
                "name": "Sex",
                "categories": ["Male", "Female"],
                "candidate_variable": "SEX",
                "denominator_rule": "displayed_categories",
            },
            {
                "name": "Smoking status",
                "categories": ["Yes", "No"],
                "candidate_variable": None,
            },
        ],
        "requested_statistics": ["count", "mean", "sd", "median", "min", "max"],
        "unresolved_items": [{"type": "warning", "message": "Population is missing."}],
        "assumptions": [{"field": "population", "value": "ITT Population"}],
    }

    result = generate_r_code(plan)
    assert isinstance(result, GenerationResult)
    code = result.code

    assert "# Assumptions:" in code
    assert "# - field=population, value=ITT Population" in code
    assert "# Unresolved items:" in code
    assert "# - type=warning, message=Population is missing." in code
    assert 'treatment_columns <- c("Group 1", "Group 2", "Group 3")' in code

    assert "continuous_age_yr <- adsl %>%" in code
    assert 'group_by(.data[["TRT_GROUP"]]) %>%' in code
    assert (
        'mean = ifelse(sum(!is.na(.data[["AGE"]])) > 0, mean(.data[["AGE"]], na.rm = TRUE), NA_real_)'
        in code
    )
    assert (
        'max = ifelse(sum(!is.na(.data[["AGE"]])) > 0, max(.data[["AGE"]], na.rm = TRUE), NA_real_)'
        in code
    )

    assert "categorical_sex <- adsl %>%" in code
    assert "# Denominator rule: displayed_categories" in code
    assert 'filter(.data[["SEX"]] %in% c("Male", "Female"))' in code
    assert 'count(.data[["TRT_GROUP"]], .data[["SEX"]], name = "n")' in code
    assert "mutate(percent = ifelse(sum(n) > 0, 100 * n / sum(n), NA_real_))" in code

    assert '# TODO: map candidate_variable for continuous section "Height (cm)"' in code
    assert '# TODO: map candidate_variable for categorical section "Smoking status"' in code
    assert "Assumption: field=population, value=ITT Population" in result.warnings
    assert (
        "Unresolved item: type=warning, message=Population is missing."
        in result.warnings
    )
    assert result.unsupported_statistics == []
    assert (
        "continuous_sections.Height (cm).candidate_variable"
        in result.unresolved_dependencies
    )
    assert (
        "categorical_sections.Smoking status.candidate_variable"
        in result.unresolved_dependencies
    )


def test_generate_r_code_handles_empty_assumptions_and_unresolved_items() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": None,
        "group_variable": None,
        "treatment_columns": [],
        "continuous_sections": [],
        "categorical_sections": [],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "# - none" in code
    assert "library(dplyr)" in code
    assert "Missing dependency: plan.group_variable for grouped summaries." in result.warnings
    assert "Missing dependency: plan.source_dataset for summary blocks." in result.warnings
    assert "plan.group_variable" in result.unresolved_dependencies
    assert "plan.source_dataset" in result.unresolved_dependencies


def test_generate_r_code_todos_when_grouping_context_missing() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": None,
        "group_variable": None,
        "treatment_columns": [],
        "continuous_sections": [
            {
                "name": "Age (yr)",
                "statistics": ["mean"],
                "candidate_variable": "AGE",
            }
        ],
        "categorical_sections": [
            {
                "name": "Sex",
                "categories": ["Male", "Female"],
                "candidate_variable": "SEX",
                "denominator_rule": "displayed_categories",
            }
        ],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "# TODO: set plan.group_variable to enable grouped summary generation" in code
    assert '# TODO: set plan.source_dataset before generating grouped continuous section "Age (yr)"' in code
    assert '# TODO: set plan.source_dataset before generating grouped categorical section "Sex"' in code
    assert "continuous_age_yr <- " not in code
    assert "categorical_sex <- " not in code
    assert "plan.source_dataset" in result.unresolved_dependencies
    assert "plan.group_variable" in result.unresolved_dependencies


def test_generate_r_code_records_unsupported_statistics() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [
            {
                "name": "Age (yr)",
                "statistics": ["mean", "iqr"],
                "candidate_variable": "AGE",
            }
        ],
        "categorical_sections": [],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert '# TODO: unsupported statistics ignored for section "Age (yr)": iqr' in code
    assert result.unsupported_statistics == [
        {
            "section_type": "continuous",
            "section_name": "Age (yr)",
            "candidate_variable": "AGE",
            "statistics": ["iqr"],
        }
    ]


def test_generate_r_code_categorical_nonmissing_denominator_rule() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [],
        "categorical_sections": [
            {
                "name": "Sex",
                "categories": ["Male", "Female"],
                "candidate_variable": "SEX",
                "denominator_rule": "nonmissing",
            }
        ],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "# Denominator rule: nonmissing" in code
    assert "categorical_sex_denom <- adsl %>%" in code
    assert 'filter(!is.na(.data[["SEX"]])) %>%' in code
    assert 'count(.data[["TRT_GROUP"]], name = "denom_n")' in code
    assert 'left_join(categorical_sex_denom, by = c("TRT_GROUP")) %>%' in code
    assert "mutate(percent = ifelse(denom_n > 0, 100 * n / denom_n, NA_real_)) %>%" in code


def test_generate_r_code_categorical_group_total_denominator_rule() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [],
        "categorical_sections": [
            {
                "name": "Sex",
                "categories": ["Male", "Female"],
                "candidate_variable": "SEX",
                "denominator_rule": "group_total",
            }
        ],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "# Denominator rule: group_total" in code
    assert "categorical_sex_denom <- adsl %>%" in code
    assert 'count(.data[["TRT_GROUP"]], name = "denom_n")' in code
    assert 'left_join(categorical_sex_denom, by = c("TRT_GROUP")) %>%' in code
    assert "mutate(percent = ifelse(denom_n > 0, 100 * n / denom_n, NA_real_)) %>%" in code


def test_generate_r_code_categorical_missing_denominator_rule_todo() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [],
        "categorical_sections": [
            {
                "name": "Sex",
                "categories": ["Male", "Female"],
                "candidate_variable": "SEX",
            }
        ],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert (
        '# TODO: set denominator_rule for categorical section "Sex" (displayed_categories, nonmissing, group_total)'
        in code
    )
    assert "categorical_sex <- adsl %>%" not in code
    assert "categorical_sections.Sex.denominator_rule" in result.unresolved_dependencies


def test_generate_r_code_object_names_use_section_id_for_duplicates() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [
            {
                "id": "cont-001",
                "name": "Age (yr)",
                "statistics": ["mean"],
                "candidate_variable": "AGE",
            },
            {
                "id": "cont-002",
                "name": "Age (yr)",
                "statistics": ["mean"],
                "candidate_variable": "AGEBL",
            },
        ],
        "categorical_sections": [],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "continuous_age_yr <- adsl %>%" in code
    assert "continuous_age_yr_cont_002 <- adsl %>%" in code


def test_generate_r_code_object_names_use_index_for_near_duplicate_names() -> None:
    plan = {
        "table_title": "Simple Table",
        "dataset_hint": None,
        "source_dataset": "adsl",
        "group_variable": "TRT_GROUP",
        "treatment_columns": [],
        "continuous_sections": [],
        "categorical_sections": [
            {
                "name": "Smoking status",
                "categories": ["Yes", "No"],
                "candidate_variable": "SMOKE",
                "denominator_rule": "displayed_categories",
            },
            {
                "name": "Smoking-status",
                "categories": ["Current", "Former", "Never"],
                "candidate_variable": "SMOKEST",
                "denominator_rule": "displayed_categories",
            },
        ],
        "requested_statistics": [],
        "unresolved_items": [],
        "assumptions": [],
    }

    result = generate_r_code(plan)
    code = result.code

    assert "categorical_smoking_status <- adsl %>%" in code
    assert "categorical_smoking_status_2 <- adsl %>%" in code
