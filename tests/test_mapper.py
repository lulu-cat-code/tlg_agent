from src.mapper import map_docx_fields_to_csv


class FakeLLMEngine:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def apply(self, *, plan, feedback=None):
        self.calls.append({"plan": plan, "feedback": feedback})
        return self.response


def test_map_docx_fields_to_csv_delegates_to_llm_engine() -> None:
    plan = {
        "title": "Demo",
        "mapping_tasks": [{"group_name": "Age (yr)"}],
    }
    response = {"mapping_tasks": [{"group_name": "Age (yr)", "candidate_csv_column": "AGE"}]}
    engine = FakeLLMEngine(response)

    mapped = map_docx_fields_to_csv(plan, engine, feedback=["fix mapping"])

    assert mapped == response
    assert engine.calls == [{"plan": plan, "feedback": ["fix mapping"]}]
