from types import SimpleNamespace

from src.reviewer import ReviewResult, review_generation


def test_review_generation_pass_case() -> None:
    generation = SimpleNamespace(
        code='result <- adsl %>% summarise(n = n(), .groups = "drop")\n',
        warnings=[],
        unsupported_statistics=[],
        unresolved_dependencies=[],
    )

    result = review_generation(generation)

    assert isinstance(result, ReviewResult)
    assert result.status == "pass"
    assert result.issues == []
    assert result.warnings == []
    assert result.suggestions == []


def test_review_generation_warn_case_with_todo() -> None:
    generation = SimpleNamespace(
        code='# TODO: map variable\nresult <- adsl %>% summarise(n = n(), .groups = "drop")\n',
        warnings=[],
        unsupported_statistics=[],
        unresolved_dependencies=[],
    )

    result = review_generation(generation)

    assert result.status == "warn"
    assert result.issues == []
    assert "Generated code still contains TODO markers." in result.warnings
    assert "Resolve TODO markers in generated code." in result.suggestions


def test_review_generation_fail_case_with_unresolved_dependency() -> None:
    generation = SimpleNamespace(
        code='result <- adsl %>% summarise(n = n(), .groups = "drop")\n',
        warnings=[],
        unsupported_statistics=[],
        unresolved_dependencies=["plan.group_variable"],
    )

    result = review_generation(generation)

    assert result.status == "fail"
    assert "Unresolved dependencies: plan.group_variable" in result.issues
    assert (
        "Resolve all dependencies in generation.unresolved_dependencies before execution."
        in result.suggestions
    )


def test_review_generation_fail_case_with_empty_code() -> None:
    generation = SimpleNamespace(
        code="# heading only\n# still comment\n",
        warnings=[],
        unsupported_statistics=[],
        unresolved_dependencies=[],
    )

    result = review_generation(generation)

    assert result.status == "fail"
    assert "Generated code is empty or only comments." in result.issues
    assert "Generate executable R statements before release." in result.suggestions
