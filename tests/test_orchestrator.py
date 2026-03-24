from types import SimpleNamespace

from src.orchestrator import OrchestrationResult, run_pipeline
from src.reviewer import ReviewResult
from src.runner import RunResult


def test_run_pipeline_full_pass_flow(monkeypatch) -> None:
    parsed = {"spec": 1}
    planned = {"plan": 1}
    mapped = {"mapped": 1}
    generation = SimpleNamespace(code='x <- 1\nsummarise(.groups = "drop")\n')
    review = ReviewResult(status="pass", issues=[], warnings=[], suggestions=[])
    run_result = RunResult(
        success=True, stdout="ok", stderr="", returncode=0, script_path="/tmp/x.R"
    )

    monkeypatch.setattr("src.orchestrator.interpret_parser_spec", lambda _: parsed)
    monkeypatch.setattr("src.orchestrator.build_analysis_plan", lambda _: planned)
    monkeypatch.setattr("src.orchestrator.map_candidate_variables", lambda _: mapped)
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda _: generation)
    monkeypatch.setattr("src.orchestrator.review_generation", lambda _: review)
    monkeypatch.setattr("src.orchestrator.run_r_code", lambda _: run_result)

    result = run_pipeline("dummy shell text")

    assert isinstance(result, OrchestrationResult)
    assert result.parsed == parsed
    assert result.planned == planned
    assert result.mapped == mapped
    assert result.generation == generation
    assert result.review == review
    assert result.run_result == run_result
    assert result.stopped_stage is None
    assert result.error_message is None
    assert result.success is True


def test_run_pipeline_warn_flow_still_runs(monkeypatch) -> None:
    generation = SimpleNamespace(code='x <- 1\nsummarise(.groups = "drop")\n')
    review = ReviewResult(
        status="warn",
        issues=[],
        warnings=["Generated code still contains TODO markers."],
        suggestions=["Resolve TODO markers in generated code."],
    )
    run_result = RunResult(
        success=True, stdout="ok", stderr="", returncode=0, script_path="/tmp/x.R"
    )
    called = {"runner": 0}

    monkeypatch.setattr("src.orchestrator.interpret_parser_spec", lambda _: {})
    monkeypatch.setattr("src.orchestrator.build_analysis_plan", lambda _: {})
    monkeypatch.setattr("src.orchestrator.map_candidate_variables", lambda _: {})
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda _: generation)
    monkeypatch.setattr("src.orchestrator.review_generation", lambda _: review)

    def fake_runner(_: str) -> RunResult:
        called["runner"] += 1
        return run_result

    monkeypatch.setattr("src.orchestrator.run_r_code", fake_runner)

    result = run_pipeline("dummy shell text")

    assert called["runner"] == 1
    assert result.stopped_stage is None
    assert result.error_message is None
    assert result.success is True
    assert result.review.status == "warn"
    assert result.run_result == run_result


def test_run_pipeline_fail_review_stops_before_runner(monkeypatch) -> None:
    generation = SimpleNamespace(code='x <- 1\nsummarise(.groups = "drop")\n')
    review = ReviewResult(
        status="fail",
        issues=["Unresolved dependencies: plan.group_variable"],
        warnings=[],
        suggestions=["Resolve dependencies"],
    )
    called = {"runner": 0}

    monkeypatch.setattr("src.orchestrator.interpret_parser_spec", lambda _: {})
    monkeypatch.setattr("src.orchestrator.build_analysis_plan", lambda _: {})
    monkeypatch.setattr("src.orchestrator.map_candidate_variables", lambda _: {})
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda _: generation)
    monkeypatch.setattr("src.orchestrator.review_generation", lambda _: review)

    def fake_runner(_: str) -> RunResult:
        called["runner"] += 1
        return RunResult(
            success=True, stdout="ok", stderr="", returncode=0, script_path="/tmp/x.R"
        )

    monkeypatch.setattr("src.orchestrator.run_r_code", fake_runner)

    result = run_pipeline("dummy shell text")

    assert called["runner"] == 0
    assert result.run_result is None
    assert result.stopped_stage == "reviewer"
    assert result.error_message is None
    assert result.success is False


def test_run_pipeline_exception_at_stage(monkeypatch) -> None:
    monkeypatch.setattr("src.orchestrator.interpret_parser_spec", lambda _: {"p": 1})
    monkeypatch.setattr("src.orchestrator.build_analysis_plan", lambda _: {"pl": 1})

    def fail_mapper(_: dict) -> dict:
        raise RuntimeError("mapper failure")

    monkeypatch.setattr("src.orchestrator.map_candidate_variables", fail_mapper)

    result = run_pipeline("dummy shell text")

    assert result.parsed == {"p": 1}
    assert result.planned == {"pl": 1}
    assert result.mapped is None
    assert result.generation is None
    assert result.review is None
    assert result.run_result is None
    assert result.stopped_stage == "mapper"
    assert result.error_message == "mapper failure"
    assert result.success is False


def test_run_pipeline_runner_failure_after_warning_review(monkeypatch) -> None:
    generation = SimpleNamespace(code='x <- 1\nsummarise(.groups = "drop")\n')
    review = ReviewResult(status="warn", issues=[], warnings=["w"], suggestions=["s"])
    run_result = RunResult(
        success=False,
        stdout="",
        stderr="Execution failed",
        returncode=1,
        script_path="/tmp/x.R",
    )

    monkeypatch.setattr("src.orchestrator.interpret_parser_spec", lambda _: {})
    monkeypatch.setattr("src.orchestrator.build_analysis_plan", lambda _: {})
    monkeypatch.setattr("src.orchestrator.map_candidate_variables", lambda _: {})
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda _: generation)
    monkeypatch.setattr("src.orchestrator.review_generation", lambda _: review)
    monkeypatch.setattr("src.orchestrator.run_r_code", lambda _: run_result)

    result = run_pipeline("dummy shell text")

    assert result.stopped_stage is None
    assert result.error_message is None
    assert result.review.status == "warn"
    assert result.run_result == run_result
    assert result.success is False
