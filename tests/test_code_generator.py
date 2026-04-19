from src.code_generator import GenerationResult, generate_r_code


class FakeLLMEngine:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def generate_r_script(self, *, mapped_plan, feedback=None):
        self.calls.append({"mapped_plan": mapped_plan, "feedback": feedback})
        return self.payload


def test_generate_r_code_uses_llm_output_and_collects_unresolved_mappings() -> None:
    plan = {
        "mapping_tasks": [
            {"group_name": "Age (yr)", "candidate_csv_column": "AGE"},
            {"group_name": "Sex", "candidate_csv_column": None},
        ],
        "unresolved": ["Smoking status"],
    }
    engine = FakeLLMEngine({"code": "cat('ok')\n", "warnings": ["check labels"]})

    result = generate_r_code(plan, llm_engine=engine, feedback=["retry"])

    assert isinstance(result, GenerationResult)
    assert result.code == "cat('ok')\n"
    assert result.warnings == ["check labels"]
    assert result.unresolved_mappings == ["Sex", "Smoking status"]
    assert result.unsupported_statistics == []
    assert result.unresolved_dependencies == []
    assert engine.calls == [{"mapped_plan": plan, "feedback": ["retry"]}]
