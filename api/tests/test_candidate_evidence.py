"""Model-free contracts for isolated candidate propositions and GLiNER cues."""

from __future__ import annotations

import json
from typing import Any

import pytest

from app.services.candidate_evidence import (
    CANDIDATE_EVIDENCE_CUE_LABELS,
    CandidateEvidenceExtractionError,
    build_candidate_evidence,
    composer_projection,
    extract_semantic_cues,
    iter_candidate_sources,
    validate_provenance,
)
from app.services.requirement_extractor import GlinerRuntime


CLAIMS = [
    {
        "statement": "Developed web application features",
        "support": "explicit",
        "source_excerpt": "Developed web application features.",
        "associated_concepts": [],
    },
    {
        "statement": "Worked in Agile/Scrum delivery",
        "support": "explicit",
        "source_excerpt": "Worked in Agile/Scrum delivery.",
        "associated_concepts": [{"kind": "method", "value": "Agile/Scrum", "relation": "within"}],
    },
    {
        "statement": "Authored unit and integration tests",
        "support": "explicit",
        "source_excerpt": "Authored unit and integration tests.",
        "associated_concepts": [],
    },
    {
        "statement": "Deployed containerized applications",
        "support": "explicit",
        "source_excerpt": "Deployed containerized applications with Docker and CI/CD.",
        "associated_concepts": [
            {"kind": "technology", "value": "Docker", "relation": "deployed_with"},
            {"kind": "technology", "value": "CI/CD", "relation": "deployed_with"},
        ],
    },
]


def _span(source: str, value: str, label: str = "technology", confidence: float = 0.91) -> dict[str, Any]:
    start = source.index(value)
    return {"text": value, "start": start, "end": start + len(value), "confidence": confidence, "label": label}


class CueModel:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def extract_entities(self, text: str, labels: dict[str, str], **_kwargs: Any) -> dict[str, Any]:
        self.calls.append((text, tuple(labels)))
        entities: dict[str, list[dict[str, Any]]] = {}
        for technology in ("Docker", "CI/CD", "Angular", "Laravel", "Ionic"):
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


def _source_results(library: list[dict[str, Any]], claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source = iter_candidate_sources(library)[0]
    return [{"source_id": source.source_id, "claims": claims}]


def test_gliner_cues_are_supporting_only_and_keep_exact_source_offsets() -> None:
    source = iter_candidate_sources(_library("Deployed containerized applications with Docker and CI/CD."))[0]
    model = CueModel()
    cues, model_name, revision, warning = extract_semantic_cues(source, GlinerRuntime(model=model))

    assert not warning
    assert model_name == "fastino/gliner2.5-small-v1"
    assert revision
    assert model.calls == [(source.text, tuple(CANDIDATE_EVIDENCE_CUE_LABELS))]
    assert {cue.text for cue in cues} == {"Docker", "CI/CD"}
    assert all(source.text[cue.start:cue.end] == cue.text for cue in cues)
    assert "evidence_claim" not in model.calls[0][1]


def test_proposition_projection_is_independent_of_source_bullet_boundaries_and_order() -> None:
    variants = [
        [{"type": "bullet_list", "items": [{"text": claim["source_excerpt"]}]} for claim in CLAIMS],
        [
            {"type": "bullet_list", "items": [{"text": " ".join(claim["source_excerpt"] for claim in CLAIMS[:2])}]},
            {"type": "bullet_list", "items": [{"text": " ".join(claim["source_excerpt"] for claim in CLAIMS[2:])}]},
        ],
        " ".join(claim["source_excerpt"] for claim in CLAIMS),
        " ".join(claim["source_excerpt"] for claim in reversed(CLAIMS)),
    ]

    projections = []
    for description in variants:
        library = _library(description)
        source = iter_candidate_sources(library)[0]
        extracted = build_candidate_evidence(
            library,
            [{"source_id": source.source_id, "claims": CLAIMS}],
            semantic_cue_model="gliner2.5-small-v1",
            semantic_cue_model_revision="fixture",
        )
        projections.append(composer_projection(extracted).model_dump(mode="json"))

    assert all(projection == projections[0] for projection in projections[1:])
    assert {claim["statement"] for claim in projections[0]["groups"][0]["claims"]} == {
        "Developed web application features",
        "Worked in Agile/Scrum delivery",
        "Authored unit and integration tests",
        "Deployed containerized applications",
    }


def test_projection_preserves_structured_facts_and_relations_but_hides_provenance() -> None:
    description = "Deployed containerized applications with Docker and CI/CD."
    library = _library(description)
    results = _source_results(library, [CLAIMS[3]])
    extraction = build_candidate_evidence(
        library,
        results,
        semantic_cue_model="gliner2.5-small-v1",
        semantic_cue_model_revision="test",
    )
    internal = extraction.groups[0].claims[0]
    validate_provenance(
        extraction,
        {("library-experience", "experience-brain-station", "description"): description},
    )

    projection = composer_projection(extraction).model_dump(mode="json")
    encoded = json.dumps(projection)
    group = projection["groups"][0]
    assert group["identity"]["position"] == "Associate Software Engineer"
    assert group["structured_facts"]["date"] == "2022-01"
    assert group["structured_facts"]["items"] == ["Python", "TypeScript"]
    assert group["structured_facts"]["credential_url"] == "https://example.test/credential"
    assert {item["value"] for item in group["claims"][0]["associated_concepts"]} == {"Docker", "CI/CD"}
    assert {item["relation"] for item in group["claims"][0]["associated_concepts"]} == {"deployed_with"}
    assert internal.provenance.source_excerpt == description
    for key in ("library_entry_id", "source_field", "source_hash", "source_start", "source_end", "source_excerpt"):
        assert key not in encoded


def test_source_hashes_offsets_and_ids_resolve_after_rich_text_flattening() -> None:
    description = [
        {"id": "rich-block-1", "type": "bullet_list", "items": [{"id": "bullet-1", "text": "Wrote unit and integration tests.", "style": {"bold": True}}]},
        {"id": "rich-block-2", "type": "bullet_list", "items": [{"id": "bullet-2", "text": "Deployed containerized applications with Docker and CI/CD.", "style": {"italic": True}}]},
    ]
    library = _library(description)
    source = iter_candidate_sources(library)[0]
    claims = [
        {
            "statement": "Authored unit and integration tests",
            "support": "explicit",
            "source_excerpt": "Wrote unit and integration tests.",
            "associated_concepts": [],
        },
        CLAIMS[3],
    ]
    extraction = build_candidate_evidence(
        library,
        [{"source_id": source.source_id, "claims": claims}],
        semantic_cue_model="gliner2.5-small-v1",
        semantic_cue_model_revision="test",
    )
    validate_provenance(
        extraction,
        {("library-experience", "experience-brain-station", "description"): source.text},
    )
    projection = composer_projection(extraction).model_dump(mode="json")
    encoded = json.dumps(projection)
    assert "rich-block" not in encoded
    assert "bullet-1" not in encoded
    assert "source_start" not in encoded
    assert [claim["id"] for claim in projection["groups"][0]["claims"]] == sorted(
        claim["id"] for claim in projection["groups"][0]["claims"]
    )


def test_claim_must_be_short_source_grounded_and_relations_must_be_local() -> None:
    description = "Deployed containerized applications with Docker and CI/CD."
    library = _library(description)
    source = iter_candidate_sources(library)[0]
    invalid = [
        {"statement": "Invented Azure platform deployment", "support": "explicit", "source_excerpt": "Azure platform deployment", "associated_concepts": []},
        {"statement": "Deployed containerized applications", "support": "explicit", "source_excerpt": description, "associated_concepts": [{"kind": "technology", "value": "Azure", "relation": "deployed_with"}]},
        {"statement": "Developed applications and provisioned multiple Linux environments and authored all unit and integration tests and deployed containerized applications for several teams", "support": "explicit", "source_excerpt": description, "associated_concepts": []},
        {"statement": "A non-explicit inferred skill", "support": "strong_ecosystem_inference", "source_excerpt": description, "associated_concepts": []},
    ]
    for claim in invalid:
        with pytest.raises(CandidateEvidenceExtractionError):
            build_candidate_evidence(
                library,
                [{"source_id": source.source_id, "claims": [claim]}],
                semantic_cue_model="gliner2.5-small-v1",
                semantic_cue_model_revision="test",
            )


def test_claim_rejects_a_multi_sentence_provenance_excerpt() -> None:
    excerpt = "Deployed containerized applications with Docker. " + ("Additional unrelated context. " * 9)
    source = iter_candidate_sources(_library(excerpt))[0]
    with pytest.raises(CandidateEvidenceExtractionError, match="excerpt is too broad"):
        build_candidate_evidence(
            _library(excerpt),
            [{
                "source_id": source.source_id,
                "claims": [{
                    "statement": "Deployed containerized applications",
                    "support": "explicit",
                    "source_excerpt": excerpt,
                    "associated_concepts": [],
                }],
            }],
            semantic_cue_model="gliner2.5-small-v1",
            semantic_cue_model_revision="test",
        )


def test_extraction_rejects_missing_duplicate_and_cross_source_results() -> None:
    library = _library("Built web features.")
    first_source = iter_candidate_sources(library)[0]
    second_library = _library("Researched interface accessibility.")
    library[0]["payload"].append(second_library[0]["payload"][0] | {"id": "another-row"})
    sources = iter_candidate_sources(library)
    claim = {"statement": "Built web features", "support": "explicit", "source_excerpt": "Built web features.", "associated_concepts": []}

    with pytest.raises(CandidateEvidenceExtractionError, match="cover each narrative source"):
        build_candidate_evidence(library, [{"source_id": sources[0].source_id, "claims": [claim]}], semantic_cue_model="g", semantic_cue_model_revision="r")
    with pytest.raises(CandidateEvidenceExtractionError, match="duplicate source ID"):
        build_candidate_evidence(
            library,
            [
                {"source_id": sources[0].source_id, "claims": [claim]},
                {"source_id": sources[0].source_id, "claims": [claim]},
            ],
            semantic_cue_model="g",
            semantic_cue_model_revision="r",
        )
    assert first_source.source_id in {source.source_id for source in sources}


def test_structured_facts_survive_without_narrative_claims() -> None:
    library = _library(" ")
    assert not iter_candidate_sources(library)
    extraction = build_candidate_evidence(
        library,
        [],
        semantic_cue_model="gliner2.5-small-v1",
        semantic_cue_model_revision="test",
    )
    projection = composer_projection(extraction).model_dump(mode="json")
    assert projection["groups"][0]["identity"]["company"] == "Brain Station"
    assert projection["groups"][0]["structured_facts"]["items"] == ["Python", "TypeScript"]
    assert projection["groups"][0]["claims"] == []
