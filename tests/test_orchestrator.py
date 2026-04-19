from types import SimpleNamespace

from src.llm_agent import LLMUnavailableError
from src.orchestrator import OrchestrationResult, run_pipeline
from src.reviewer import ReviewResult


def test_run_pipeline_full_pass_flow(monkeypatch) -> None:
    parsed = {"docx_spec": 1}
    planned = {"plan": 1}
    mapped = {"mapped": 1}
    generation = SimpleNamespace(code='trt_levels <- unique(data[["TRT_GROUP"]])\ntolower("x")\nPlacebo\nn\n')
    review = ReviewResult(status="pass", issues=[], warnings=[], suggestions=[])

    monkeypatch.setattr("src.orchestrator.parse_inputs", lambda **_: parsed)
    monkeypatch.setattr("src.orchestrator.build_generation_plan", lambda **_: planned)
    monkeypatch.setattr(
        "src.orchestrator.LLMDecisionEngine",
        lambda model: SimpleNamespace(get_usage_summary=lambda: {"calls": []}),
    )
    monkeypatch.setattr("src.orchestrator.map_docx_fields_to_csv", lambda **_: mapped)
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda *args, **kwargs: generation)
    monkeypatch.setattr(
        "src.orchestrator.validate_code_against_blueprint",
        lambda code, mapped_plan: SimpleNamespace(ok=True, issues=[]),
    )
    monkeypatch.setattr("src.orchestrator.review_generation", lambda generation: review)

    result = run_pipeline("shell.docx", "data/adsl.csv", "TRT_GROUP")

    assert isinstance(result, OrchestrationResult)
    assert result.parsed == parsed
    assert result.planned == planned
    assert result.mapped == mapped
    assert result.generation == generation
    assert result.review == review
    assert result.run_result is None
    assert result.stopped_stage is None
    assert result.error_message is None
    assert result.success is True


def test_run_pipeline_validation_feedback_retries(monkeypatch) -> None:
    parsed = {"docx_spec": 1}
    planned = {"plan": 1}
    mapped = {"mapped": 1}
    generation = SimpleNamespace(code='trt_levels <- unique(data[["TRT_GROUP"]])\ntolower("x")\nPlacebo\nn\n')
    feedback_calls = []
    validations = iter(
        [
            SimpleNamespace(ok=False, issues=["missing trt mapping"]),
            SimpleNamespace(ok=True, issues=[]),
        ]
    )

    monkeypatch.setattr("src.orchestrator.parse_inputs", lambda **_: parsed)
    monkeypatch.setattr("src.orchestrator.build_generation_plan", lambda **_: planned)
    monkeypatch.setattr(
        "src.orchestrator.LLMDecisionEngine",
        lambda model: SimpleNamespace(get_usage_summary=lambda: {"calls": []}),
    )

    def fake_map(*, plan, llm_engine, feedback):
        feedback_calls.append(list(feedback))
        return mapped

    monkeypatch.setattr("src.orchestrator.map_docx_fields_to_csv", fake_map)
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda *args, **kwargs: generation)
    monkeypatch.setattr(
        "src.orchestrator.validate_code_against_blueprint",
        lambda code, mapped_plan: next(validations),
    )
    monkeypatch.setattr("src.orchestrator.review_generation", lambda generation: None)

    result = run_pipeline("shell.docx", "data/adsl.csv", "TRT_GROUP", max_revision_rounds=1)

    assert feedback_calls == [[], ["missing trt mapping"]]
    assert result.success is True
    assert result.error_message is None
    assert result.validation_issues == ["missing trt mapping"]


def test_run_pipeline_llm_unavailable_stops_before_mapping(monkeypatch) -> None:
    parsed = {"docx_spec": 1}
    planned = {"plan": 1}

    monkeypatch.setattr("src.orchestrator.parse_inputs", lambda **_: parsed)
    monkeypatch.setattr("src.orchestrator.build_generation_plan", lambda **_: planned)

    def fail_llm(model):
        raise LLMUnavailableError("OPENAI_API_KEY is not set.")

    monkeypatch.setattr("src.orchestrator.LLMDecisionEngine", fail_llm)

    result = run_pipeline("shell.docx", "data/adsl.csv", "TRT_GROUP")

    assert result.parsed == parsed
    assert result.planned == planned
    assert result.mapped is None
    assert result.generation is None
    assert result.stopped_stage == "mapper"
    assert result.error_message == "OPENAI_API_KEY is not set."
    assert result.success is False
    assert result.validation_issues == []


def test_run_pipeline_schema_flow_runs_optimizer_before_validate(monkeypatch) -> None:
    parsed = {"docx_spec": {}, "csv_schema": {}}
    planned = {"tables": []}
    mapped = {"tables": []}
    generation = SimpleNamespace(code="x <- 1\n\n\n", warnings=[])
    review = ReviewResult(status="pass", issues=[], warnings=[], suggestions=[])
    seen = {"validated_code": None}

    class DummyEngine:
        def get_usage_summary(self) -> dict:
            return {"calls": []}

    monkeypatch.setattr("src.orchestrator.parse_inputs", lambda **_: parsed)
    monkeypatch.setattr("src.orchestrator.build_generation_plan", lambda **_: planned)
    monkeypatch.setattr("src.orchestrator.LLMDecisionEngine", lambda model: DummyEngine())
    monkeypatch.setattr("src.orchestrator.map_docx_fields_to_csv", lambda **_: mapped)
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda *_, **__: generation)

    def fake_optimize(generation_obj, mapped_plan):
        assert generation_obj is generation
        assert mapped_plan is mapped
        generation_obj.code = "x <- 1\n# optimized\n"
        return generation_obj

    def fake_validate(code: str, mapped_plan: dict) -> SimpleNamespace:
        seen["validated_code"] = code
        assert mapped_plan is mapped
        return SimpleNamespace(ok=True, issues=[])

    monkeypatch.setattr("src.orchestrator.optimize_generated_code", fake_optimize)
    monkeypatch.setattr("src.orchestrator.validate_code_against_blueprint", fake_validate)
    monkeypatch.setattr("src.orchestrator.review_generation", lambda _: review)

    result = run_pipeline(
        docx_filename="shell.docx",
        csv_path="data/adsl.csv",
        trt_group_name="TRT01A",
    )

    assert result.success is True
    assert result.generation.code == "x <- 1\n# optimized\n"
    assert seen["validated_code"] == "x <- 1\n# optimized\n"


def test_run_pipeline_schema_flow_optimizer_failure_stops_pipeline(monkeypatch) -> None:
    parsed = {"docx_spec": {}, "csv_schema": {}}
    planned = {"tables": []}
    mapped = {"tables": []}
    generation = SimpleNamespace(code="x <- 1\n", warnings=[])

    class DummyEngine:
        def get_usage_summary(self) -> dict:
            return {"calls": []}

    monkeypatch.setattr("src.orchestrator.parse_inputs", lambda **_: parsed)
    monkeypatch.setattr("src.orchestrator.build_generation_plan", lambda **_: planned)
    monkeypatch.setattr("src.orchestrator.LLMDecisionEngine", lambda model: DummyEngine())
    monkeypatch.setattr("src.orchestrator.map_docx_fields_to_csv", lambda **_: mapped)
    monkeypatch.setattr("src.orchestrator.generate_r_code", lambda *_, **__: generation)
    monkeypatch.setattr(
        "src.orchestrator.optimize_generated_code",
        lambda *_: (_ for _ in ()).throw(RuntimeError("optimizer failure")),
    )

    result = run_pipeline(
        docx_filename="shell.docx",
        csv_path="data/adsl.csv",
        trt_group_name="TRT01A",
    )

    assert result.success is False
    assert result.stopped_stage == "optimizer"
    assert result.error_message == "optimizer failure"
