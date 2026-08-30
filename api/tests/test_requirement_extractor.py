"""Model-free contracts for the production GLiNER2 requirement boundary."""

from __future__ import annotations

import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import ModuleType
from typing import Any

import pytest

from app.services import relevance
from app.services.requirement_extractor import (
    Gliner2RequirementExtractor,
    Importance,
    RequirementExtractionError,
    requirements_from_model_output,
    to_job_requirements,
)


def _span(source: str, value: str, *, occurrence: int = 0, confidence: float = 0.9) -> dict[str, Any]:
    start = -1
    for _ in range(occurrence + 1):
        start = source.index(value, start + 1)
    return {"text": value, "start": start, "end": start + len(value), "confidence": confidence}


class FakeEntityModel:
    def __init__(self, phrases: list[tuple[str, str]]) -> None:
        self.phrases = phrases
        self.calls: list[str] = []

    def extract_entities(self, text: str, _labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        self.calls.append(text)
        entities: dict[str, list[dict[str, Any]]] = {}
        for label, phrase in self.phrases:
            if phrase in text:
                entities.setdefault(label, []).append(_span(text, phrase))
        return {"entities": entities}


def test_normalization_excludes_boilerplate_and_preserves_eligibility() -> None:
    source = """About the Company
We build payroll software for teams.
Minimum Qualifications
Design highly available distributed services.
Python experience required.
Preferred Qualifications
AWS experience is a plus.
Compensation
Salary range is $100,000-$120,000.
Benefits
Health insurance and paid time off.
Equal Employment Opportunity
We welcome applicants of all backgrounds.
Location
Remote within Canada.
Candidates must be authorized to work in Canada.
"""
    candidate_phrases = [
        "About the Company",
        "We build payroll software for teams.",
        "Design highly available distributed services.",
        "Python experience required.",
        "AWS experience is a plus.",
        "Salary range is $100,000-$120,000.",
        "Health insurance and paid time off.",
        "We welcome applicants of all backgrounds.",
        "Remote within Canada.",
        "Candidates must be authorized to work in Canada.",
    ]
    result = requirements_from_model_output(
        source,
        {
            "entities": {
                "candidate_requirement": [_span(source, phrase) for phrase in candidate_phrases],
                "hard_skill": [_span(source, "Python"), _span(source, "AWS")],
            }
        },
    )

    assert [item.source_text for item in result.requirements] == [
        "Design highly available distributed services.",
        "Python experience required.",
        "AWS experience is a plus.",
        "Candidates must be authorized to work in Canada.",
    ]
    assert result.requirements[0].importance is Importance.REQUIRED
    assert result.requirements[2].importance is Importance.PREFERRED
    assert result.requirements[3].importance is Importance.REQUIRED
    for item in result.requirements:
        assert source[item.source_start : item.source_end] == item.source_text


def test_inline_boilerplate_does_not_hide_requirements_on_the_same_line() -> None:
    source = (
        "We require 5+ years of Python and AWS experience. "
        "You will design highly available distributed services. "
        "Kubernetes is nice to have. Salary is $150,000 and we offer health benefits."
    )
    result = requirements_from_model_output(
        source,
        {
            "entities": {
                "hard_skill": [_span(source, "Python"), _span(source, "Kubernetes")],
                "responsibility": [_span(source, "design highly available distributed services")],
                "quantitative_constraint": [_span(source, "5+ years")],
                "preferred_requirement": [_span(source, "Kubernetes"), _span(source, "health benefits")],
            }
        },
    )

    assert [item.source_text for item in result.requirements] == [
        "We require 5+ years of Python and AWS experience.",
        "You will design highly available distributed services.",
        "Kubernetes is nice to have.",
    ]
    assert result.requirements[0].importance is Importance.REQUIRED
    assert result.requirements[2].importance is Importance.PREFERRED


def test_unknown_importance_does_not_become_required() -> None:
    source = "Qualifications\nExperience with Rust is not required."
    result = requirements_from_model_output(
        source,
        {
            "entities": {
                "candidate_requirement": [_span(source, "Experience with Rust is not required.")],
                "hard_skill": [_span(source, "Rust")],
            }
        },
    )

    requirement = to_job_requirements(result)[0]
    assert requirement.importance == "unknown"
    assert requirement.required is False
    assert requirement.weight == 0.75


def test_duplicate_overlapping_candidates_merge_without_losing_required_status() -> None:
    source = "Python experience required."
    result = requirements_from_model_output(
        source,
        {
            "entities": {
                "candidate_requirement": [
                    _span(source, source),
                    _span(source, "Python experience required."),
                ],
                "preferred_requirement": [_span(source, source)],
            }
        },
    )

    assert len(result.requirements) == 1
    assert result.requirements[0].importance is Importance.REQUIRED


def test_deterministic_constraints_keep_years_and_degree_on_source_requirement() -> None:
    source = "At least three years of experience and a Bachelor's degree are required."
    result = requirements_from_model_output(
        source,
        {"entities": {"candidate_requirement": [_span(source, source)]}},
    )

    requirement = result.requirements[0]
    assert {item.kind for item in requirement.constraints} == {"years_experience", "degree_level"}
    assert {item.value for item in requirement.constraints} == {3, "bachelor"}
    assert requirement.importance is Importance.REQUIRED


def test_long_documents_use_sentence_aware_chunks_and_remap_global_spans() -> None:
    source = "\n".join(
        [
            "Minimum Qualifications",
            "Build Python APIs.",
            "".join(" supporting detail" for _ in range(4)),
            "Design distributed systems.",
            "Preferred Qualifications",
            "AWS experience is a plus.",
        ]
    )
    model = FakeEntityModel(
        [
            ("candidate_requirement", "Build Python APIs."),
            ("candidate_requirement", "Design distributed systems."),
            ("candidate_requirement", "AWS experience is a plus."),
        ]
    )
    extractor = Gliner2RequirementExtractor(model=model, chunk_size=8, chunk_overlap=2)

    result = extractor.extract_result("Platform Engineer", source)

    assert result.inference_path == "long"
    assert len(model.calls) > 1
    assert all(source[item.source_start : item.source_end] == item.source_text for item in result.requirements)
    assert {item.source_text for item in result.requirements} == {
        "Build Python APIs.",
        "Design distributed systems.",
        "AWS experience is a plus.",
    }


def test_model_loading_is_lazy_and_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    class AutoExtractor:
        @classmethod
        def from_pretrained(cls, _model_name: str, **_kwargs: Any) -> FakeEntityModel:
            nonlocal calls
            calls += 1
            return FakeEntityModel([("candidate_requirement", "Python required.")])

    module = ModuleType("gliner2")
    module.AutoExtractor = AutoExtractor  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "gliner2", module)
    extractor = Gliner2RequirementExtractor()

    assert extractor._model is None
    first = extractor.load()
    second = extractor.load()
    assert first is second
    assert calls == 1


def test_inference_concurrency_is_serialized() -> None:
    state = {"active": 0, "maximum": 0}
    state_lock = threading.Lock()

    class SlowModel:
        def extract_entities(self, text: str, _labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
            with state_lock:
                state["active"] += 1
                state["maximum"] = max(state["maximum"], state["active"])
            try:
                time.sleep(0.01)
                return {"entities": {"candidate_requirement": [_span(text, text)]}}
            finally:
                with state_lock:
                    state["active"] -= 1

    extractor = Gliner2RequirementExtractor(model=SlowModel())
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda index: extractor.extract_result("Engineer", f"Python required {index}."), range(4)))

    assert state["maximum"] == 1


def test_model_failure_is_an_extraction_error_without_old_parser_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingModel:
        def extract_entities(self, _text: str, _labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
            raise RuntimeError("model unavailable")

    extractor = Gliner2RequirementExtractor(model=FailingModel())
    monkeypatch.setattr(relevance, "extract_requirements_v2", lambda *_args: pytest.fail("old parser called"))
    monkeypatch.setattr(relevance._requirement_extractor, "get_requirement_extractor", lambda: extractor)

    with pytest.raises(RequirementExtractionError):
        relevance.extract_requirements("Engineer", "Python required.")
