from src.validator import validate_code_against_blueprint


def _mapped_plan() -> dict:
    return {
        "tables": [
            {
                "table_index": 1,
                "columns": ["Treatment A", "Treatment B"],
                "ordered_rows": [
                    {"label": "Age (yr)"},
                    {"label": "n"},
                ],
            }
        ]
    }


def test_validator_passes_allowed_packages() -> None:
    code = """
library(data.table)
library(stringr)
trt_group <- "TRT01A"
trt_levels <- unique(data[[trt_group]])
value <- tolower(trimws("Age (yr)"))
labels <- c("Treatment A", "Treatment B", "Age (yr)", "n")
"""

    result = validate_code_against_blueprint(code, _mapped_plan())

    assert result.ok is True
    assert result.issues == []


def test_validator_rejects_disallowed_library_package() -> None:
    code = """
library(data.table)
library(scales)
trt_group <- "TRT01A"
trt_levels <- unique(data[[trt_group]])
value <- tolower(trimws("Age (yr)"))
labels <- c("Treatment A", "Treatment B", "Age (yr)", "n")
"""

    result = validate_code_against_blueprint(code, _mapped_plan())

    assert result.ok is False
    assert any("disallowed R packages" in issue and "scales" in issue for issue in result.issues)


def test_validator_rejects_disallowed_namespaced_package() -> None:
    code = """
library(data.table)
trt_group <- "TRT01A"
trt_levels <- unique(data[[trt_group]])
width <- cli::ansi_strwidth("Age (yr)")
value <- tolower(trimws("Age (yr)"))
labels <- c("Treatment A", "Treatment B", "Age (yr)", "n")
"""

    result = validate_code_against_blueprint(code, _mapped_plan())

    assert result.ok is False
    assert any("disallowed R packages" in issue and "cli" in issue for issue in result.issues)


def test_validator_rejects_runtime_mapped_plan_dependency() -> None:
    code = """
library(data.table)
trt_group <- "TRT01A"
trt_levels <- unique(data[[trt_group]])
value <- tolower(trimws("Age (yr)"))
tables <- mapped_plan$tables
labels <- c("Treatment A", "Treatment B", "Age (yr)", "n")
"""

    result = validate_code_against_blueprint(code, _mapped_plan())

    assert result.ok is False
    assert any("must not depend on a runtime `mapped_plan` object" in issue for issue in result.issues)
