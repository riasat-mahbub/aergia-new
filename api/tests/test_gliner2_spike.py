from __future__ import annotations

from typing import Any

from scripts.gliner2_spike import evaluate_case
from scripts.gliner2_spike_lib import (
    Gliner2RequirementExtractor,
    Importance,
    Requirement,
    compare_requirement_sets,
    existing_v2_requirements,
    merge_requirement_sets,
    requirements_from_model_output,
)


def _span(source: str, value: str, confidence: float = 0.9) -> dict[str, Any]:
    start = source.index(value)
    return {"text": value, "start": start, "end": start + len(value), "confidence": confidence}


class FakeEntityModel:
    def __init__(self, result: dict[str, Any]) -> None:
        self.result = result
        self.short_calls = 0
        self.long_calls = 0

    def extract_entities(self, _text: str, _labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        self.short_calls += 1
        return self.result

    def extract_entities_long(self, _text: str, _labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        self.long_calls += 1
        return self.result


def test_model_output_preserves_spans_and_adds_deterministic_constraints() -> None:
    source = (
        "Minimum Qualifications\n"
        "At least three years of backend engineering experience with Python.\n"
        "Preferred Qualifications\n"
        "Kubernetes experience is a plus."
    )
    first = "At least three years of backend engineering experience with Python."
    second = "Kubernetes experience is a plus."
    result = requirements_from_model_output(
        source,
        {
            "entities": {
                "requirement": [_span(source, first), _span(source, second)],
                "skill": [_span(source, "Python"), _span(source, "Kubernetes")],
            }
        },
    )

    assert len(result.requirements) == 2
    required, preferred = result.requirements
    assert source[required.source_start : required.source_end] == required.source_text
    assert required.importance is Importance.REQUIRED
    assert "python" in required.concepts
    assert required.constraints[0].kind == "years_experience"
    assert required.constraints[0].value == 3
    assert preferred.importance is Importance.PREFERRED
    assert "kubernetes" in preferred.concepts


def test_explicit_negative_language_does_not_become_required() -> None:
    source = "Qualifications\nA bachelor's degree is not required."
    candidate = "A bachelor's degree is not required."
    result = requirements_from_model_output(
        source,
        {"entities": {"requirement": [_span(source, candidate)], "education_requirement": [_span(source, "bachelor's degree")]}},
    )

    assert result.requirements[0].importance is Importance.UNKNOWN
    assert result.requirements[0].constraints[0].kind == "degree_level"


def test_adapter_uses_long_document_api_after_chunk_threshold() -> None:
    source = "word one two three four Python requirement"
    model = FakeEntityModel({"entities": {"requirement": [_span(source, "Python requirement")]}})
    extractor = Gliner2RequirementExtractor(model=model, chunk_size=3, chunk_overlap=1)

    result = extractor.extract(source)

    assert model.short_calls == 0
    assert model.long_calls == 1
    assert result.inference_path == "long"
    assert result.requirements[0].source_text == "Python requirement"


def test_adapter_uses_short_document_api_when_under_threshold() -> None:
    source = "Build Python services."
    model = FakeEntityModel({"entities": {"requirement": [_span(source, source)]}})
    extractor = Gliner2RequirementExtractor(model=model, chunk_size=20, chunk_overlap=2)

    result = extractor.extract(source)

    assert model.short_calls == 1
    assert model.long_calls == 0
    assert result.inference_path == "short"


def test_requirement_v2_adapter_and_hybrid_merge_keep_deterministic_importance() -> None:
    source = "Preferred Qualifications\nKubernetes experience is a plus."
    baseline = existing_v2_requirements(source, role="Platform Engineer")
    semantic = requirements_from_model_output(
        source,
        {"entities": {"requirement": [_span(source, "Kubernetes experience is a plus.")]}},
    )

    hybrid = merge_requirement_sets(semantic, baseline)
    assert len(hybrid.requirements) == 1
    assert hybrid.requirements[0].importance is Importance.PREFERRED
    assert hybrid.requirements[0].extractor == "hybrid"


def test_comparison_reports_importance_changes() -> None:
    baseline = Requirement(
        id="baseline",
        source_text="Python experience",
        source_start=0,
        source_end=17,
        type="hard_skill",
        importance=Importance.REQUIRED,
        concepts=("python",),
    )
    candidate = Requirement(
        id="candidate",
        source_text="Python experience",
        source_start=0,
        source_end=17,
        type="hard_skill",
        importance=Importance.PREFERRED,
        concepts=("python",),
    )

    diff = compare_requirement_sets((baseline,), (candidate,))

    assert len(diff["importance_changed"]) == 1
    assert not diff["added"]
    assert not diff["removed"]


def test_fixture_baseline_is_executable_without_gliner_dependencies() -> None:
    source = "Minimum Qualifications\nPython experience required."
    case = {
        "id": "unit",
        "text": source,
        "expected": [{"anchor": "Python experience required", "importance": "required", "concepts": ["python"]}],
        "forbidden": [],
    }
    result = existing_v2_requirements(source, role="Engineer")

    evaluation = evaluate_case(case, result)

    assert evaluation["matched_count"] == 1
    assert evaluation["false_required_count"] == 0
