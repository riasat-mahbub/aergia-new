"""Model-free contracts for candidate-side GLiNER evidence extraction."""

from __future__ import annotations

import json
from typing import Any

from app.services.candidate_evidence import (
    CANDIDATE_EVIDENCE_LABELS,
    CandidateEvidenceExtractor,
    composer_projection,
    validate_provenance,
)
from app.services.requirement_extractor import GlinerRuntime


CLAIMS = [
    "Developed web application features.",
    "Worked with developers and designers in Agile delivery.",
    "Wrote unit and integration tests.",
    "Deployed containerized applications with Docker and CI/CD.",
]


def _span(source: str, value: str, confidence: float = 0.91) -> dict[str, Any]:
    start = source.index(value)
    return {"text": value, "start": start, "end": start + len(value), "confidence": confidence}


class CandidateModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def extract_entities(self, text: str, labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        self.calls.append((text, tuple(labels)))
        entities: dict[str, list[dict[str, Any]]] = {"evidence_claim": []}
        for claim in CLAIMS:
            if claim in text:
                entities["evidence_claim"].append(_span(text, claim))
        for technology in ("Docker", "CI/CD"):
            if technology in text:
                entities.setdefault("technology", []).append(_span(text, technology))
        return {"entities": entities}


def _library(description: Any) -> list[dict[str, Any]]:
    return [
        {
            "id": "library-experience",
            "kind": "experience",
            "payload": [
                {
                    "id": "experience-brain-station",
                    "company": "Brain Station",
                    "position": "Associate Software Engineer",
                    "start_date": "2022-01",
                    "date": "2022-01",
                    "category": "Languages",
                    "items": ["Python", "TypeScript"],
                    "proficiency": "Professional working",
                    "credential_url": "https://example.test/credential",
                    "description": description,
                }
            ],
        }
    ]


def test_bullet_split_merge_and_order_do_not_control_projected_claims() -> None:
    variants = [
        [
            {"type": "bullet_list", "items": [{"text": claim}]} for claim in CLAIMS
        ],
        [
            {"type": "bullet_list", "items": [{"text": " ".join(CLAIMS[:2])}]},
            {"type": "bullet_list", "items": [{"text": " ".join(CLAIMS[2:])}]},
        ],
        " ".join(CLAIMS),
        " ".join(reversed(CLAIMS)),
    ]

    projections = []
    for description in variants:
        runtime = GlinerRuntime(model=CandidateModel())
        extracted = CandidateEvidenceExtractor(runtime).extract(_library(description))
        projections.append(composer_projection(extracted).model_dump(mode="json"))

    assert all(projection == projections[0] for projection in projections[1:])
    assert {claim["statement"] for claim in projections[0]["groups"][0]["claims"]} == set(CLAIMS)


def test_projection_keeps_structured_facts_and_claim_relationships_but_hides_provenance() -> None:
    model = CandidateModel()
    description = "Deployed containerized applications with Docker and CI/CD."
    extraction = CandidateEvidenceExtractor(GlinerRuntime(model=model)).extract(_library(description))
    internal = extraction.groups[0].claims[0]
    source = internal.provenance.source_excerpt
    validate_provenance(extraction, {("library-experience", "description"): description})

    projection = composer_projection(extraction).model_dump(mode="json")
    encoded = json.dumps(projection)
    assert "Associate Software Engineer" in encoded
    assert "2022-01" in encoded
    assert "Python" in encoded
    assert "Professional working" in encoded
    assert "https://example.test/credential" in encoded
    assert {item["value"] for item in projection["groups"][0]["claims"][0]["associated_concepts"]} == {"Docker", "CI/CD"}
    assert source == description
    for key in ("library_entry_id", "source_field", "source_hash", "source_start", "source_end", "source_excerpt"):
        assert key not in encoded


def test_structured_fields_bypass_gliner_and_every_claim_has_exact_provenance() -> None:
    model = CandidateModel()
    description = "Wrote unit and integration tests."
    entry = _library(description)[0]
    entry["payload"][0]["position"] = "Explicitly structured engineer title"
    extraction = CandidateEvidenceExtractor(GlinerRuntime(model=model)).extract([entry])

    assert all("Explicitly structured engineer title" not in source for source, _labels in model.calls)
    assert all(set(labels) == set(CANDIDATE_EVIDENCE_LABELS) for _source, labels in model.calls)
    assert extraction.groups[0].identity["position"] == "Explicitly structured engineer title"
    validate_provenance(extraction, {("library-experience", "description"): description})


def test_projection_does_not_expose_source_order_or_raw_rich_text() -> None:
    description = [
        {"id": "rich-block-1", "type": "bullet_list", "items": [{"id": "bullet-1", "text": CLAIMS[1], "style": {"bold": True}}]},
        {"id": "rich-block-2", "type": "bullet_list", "items": [{"id": "bullet-2", "text": CLAIMS[0], "style": {"italic": True}}]},
    ]
    extraction = CandidateEvidenceExtractor(GlinerRuntime(model=CandidateModel())).extract(_library(description))
    projection = composer_projection(extraction).model_dump(mode="json")
    encoded = json.dumps(projection)

    assert "rich-block" not in encoded
    assert "bullet-1" not in encoded
    assert "source_start" not in encoded
    assert "source_end" not in encoded
    assert [item["id"] for item in projection["groups"][0]["claims"]] == sorted(
        item["id"] for item in projection["groups"][0]["claims"]
    )


def test_long_candidate_descriptions_keep_global_offsets_in_internal_provenance() -> None:
    source = "Research detail " * 450 + " Wrote unit and integration tests."
    row = _library(source)[0]
    model = CandidateModel()
    runtime = GlinerRuntime(model=model, chunk_size=128, chunk_overlap=16)
    extraction = CandidateEvidenceExtractor(runtime).extract([row])

    assert runtime.last_inference_path == "long"
    claim = next(item for item in extraction.groups[0].claims if item.statement == "Wrote unit and integration tests.")
    assert claim.provenance.source_excerpt == "Wrote unit and integration tests."
    assert claim.provenance.source_start > 0
    validate_provenance(extraction, {("library-experience", "description"): source})
