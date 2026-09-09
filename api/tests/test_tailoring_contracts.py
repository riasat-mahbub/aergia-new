"""Phase 1 protocol fixture checks against the server-side Pydantic contract."""

import json
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from pydantic import ValidationError

from app.document_schema.capabilities import capabilities_hash, renderer_capabilities
from app.models.library import LibraryEntry
from app.http_schemas.application import AIRelevanceAssessment, JobRequirement, RequirementRelevanceResult
from app.http_schemas.tailoring import (
    ReportGapChange,
    TailoringCodeExchange,
    TailoringEvidencePacket,
    TailoringEvidenceRef,
    TailoringPatch,
    TailoringSessionStatusResponse,
)
from app.services.tailoring_facts import (
    TailoringFactError,
    validate_tailoring_facts,
    validate_tailoring_section_facts,
)
from app.services.tailoring import (
    TailoringPatchError,
    TailoringService,
    _db_utcnow,
    _stored_requirements,
    build_tailoring_prompt,
    fresh_tailoring_sections,
    library_entry_content_hash,
)
from app.services.tailoring_policy import TailoringPolicyError, validate_document_delta
from app.services.tailoring_skill import build_tailoring_skill_bundle
from app.services.relevance import evaluate_ai_relevance


_FIXTURES = (
    Path(__file__).parents[2]
    / "tailoring-skill"
    / "skills"
    / "aergia-tailor"
    / "references"
    / "fixtures"
)


def test_valid_tailoring_patch_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "tailoring-patch.valid.json").read_text())
    patch = TailoringPatch.model_validate(payload)
    assert patch.protocol_version == 1
    assert [change.operation for change in patch.changes] == [
        "add_library_entry",
        "replace_description",
        "report_gap",
    ]


def test_valid_evidence_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "evidence-packet.valid.json").read_text())
    evidence = TailoringEvidencePacket.model_validate(payload)
    assert evidence.protocol_version == 1
    assert evidence.cv.id == "cv-1"
    assert evidence.target_cv is not None
    assert evidence.target_cv.sections[0]["id"] == "target-profile"
    assert evidence.protected_facts["profile"]["name"] == "Example User"


def test_renderer_capabilities_are_deterministic_and_cover_tailoring_contract():
    capabilities = renderer_capabilities()

    assert set(capabilities["document"]["section_types"]) >= {"profile", "experience", "extras"}
    assert "styles" in capabilities["document"]
    assert capabilities["document"]["limits"]["max_sections"] == 32
    assert "replace_candidate" in capabilities["tailoring"]["operations"]
    assert "replace_section" in capabilities["tailoring"]["operations"]
    assert capabilities["tailoring"]["ai_relevance"]["coverage_score_guidance"]["strong"] == 0.75
    assert capabilities_hash(capabilities) == capabilities_hash()


def test_ai_relevance_is_validated_and_aggregated_by_requirement_weight():
    requirements = [
        JobRequirement(
            id="req-python",
            text="Python",
            normalized="python",
            type="hard_skill",
            required=True,
            weight=2,
        ),
        JobRequirement(
            id="req-kafka",
            text="Kafka",
            normalized="kafka",
            type="hard_skill",
            required=False,
            weight=1,
        ),
    ]
    assessment = AIRelevanceAssessment.model_validate(
        {
            "rubric_version": "ai-relevance-v1",
            "requirements": [
                {
                    "requirement_id": "req-python",
                    "coverage": "strong",
                    "score": 0.8,
                    "confidence": 0.9,
                    "evidence": [
                        {
                            "section_id": "candidate-profile",
                            "field_path": "summary",
                            "excerpt": "Python APIs",
                        }
                    ],
                    "rationale": "The candidate directly describes Python API work.",
                },
                {
                    "requirement_id": "req-kafka",
                    "coverage": "absent",
                    "score": 0,
                    "confidence": 0.8,
                    "rationale": "No candidate evidence.",
                },
            ]
        }
    )

    result = evaluate_ai_relevance(
        assessment,
        requirements,
        [
            {
                "id": "candidate-profile",
                "type": "profile",
                "title": "Profile",
                "data": {"summary": "Python APIs"},
            }
        ],
    )

    assert result.score == 53
    assert result.required_score == 80
    assert result.preferred_score == 0
    assert [item.requirement_id for item in result.requirements] == ["req-python", "req-kafka"]


def test_invalid_tailoring_operation_fixture_is_rejected():
    payload = json.loads((_FIXTURES / "tailoring-patch.invalid-operation.json").read_text())
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(payload)


def test_tailoring_patch_rejects_unknown_fields_and_versions():
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(
            {
                "protocol_version": 1,
                "base_revision": 1,
                "base_hash": "a" * 64,
                "unexpected": True,
                "changes": [
                    {
                        "operation": "report_gap",
                        "requirement": "Kubernetes",
                        "reason": "No evidence",
                    }
                ],
            }
        )
    with pytest.raises(ValidationError):
        TailoringPatch.model_validate(
            {
                "protocol_version": 2,
                "base_revision": 1,
                "base_hash": "a" * 64,
                "changes": [
                    {
                        "operation": "report_gap",
                        "requirement": "Kubernetes",
                        "reason": "No evidence",
                    }
                ],
            }
        )


def test_tailoring_exchange_requires_protocol_version():
    assert TailoringCodeExchange.model_validate({"protocol_version": 1, "code": "x" * 16}).protocol_version == 1
    with pytest.raises(ValidationError):
        TailoringCodeExchange.model_validate({"code": "x" * 16})


def test_tailoring_prompt_keeps_the_code_out_of_the_session_url():
    skill_url = "https://aergia.example/api/v1/tailoring/skill.zip"
    prompt = build_tailoring_prompt(
        "https://aergia.example/agent/tailor/session-1",
        "code-1234567890123456",
        skill_url,
    )
    assert "https://aergia.example/agent/tailor/session-1" in prompt
    assert "One-time session code: code-1234567890123456" in prompt
    assert skill_url in prompt
    assert "approval" in prompt


def test_tailoring_skill_bundle_is_self_contained_and_deterministic():
    first = build_tailoring_skill_bundle()
    second = build_tailoring_skill_bundle()

    assert first == second
    with ZipFile(BytesIO(first.content)) as archive:
        names = set(archive.namelist())
        skill_text = archive.read("aergia-tailor/SKILL.md").decode()

    assert skill_text.startswith("---\nname: aergia-tailor\n")
    assert "aergia-tailor/scripts/validate-patch.mjs" in names
    assert "aergia-tailor/scripts/verify-cv-facts.mjs" in names
    assert "aergia-tailor/references/tailoring-patch.schema.json" in names


def test_web_evidence_requires_a_safe_bounded_citation():
    citation = TailoringEvidenceRef.model_validate(
        {
            "source": "web",
            "url": "example.com/technical-guide",
            "title": "Technical guide",
            "excerpt": "The guide describes the relevant contextual behavior.",
        }
    )
    assert citation.url == "https://example.com/technical-guide"
    with pytest.raises(ValidationError):
        TailoringEvidenceRef.model_validate(
            {
                "source": "web",
                "url": "javascript:alert(1)",
                "title": "Unsafe",
                "excerpt": "Not a valid web citation.",
            }
        )
    with pytest.raises(ValidationError):
        TailoringEvidenceRef.model_validate(
            {
                "source": "web",
                "url": "https://example.com/guide",
                "title": "Missing excerpt",
            }
        )


def test_reported_gap_feedback_is_attached_to_the_stable_requirement():
    relevance = RequirementRelevanceResult.model_validate(
        {
            "status": "evaluated",
            "score": 0,
            "requirements": [
                {
                    "requirement": {
                        "id": "req-python",
                        "text": "Python",
                        "normalized": "python",
                        "canonical": "python",
                        "type": "hard_skill",
                        "required": True,
                        "weight": 1,
                    },
                    "covered": False,
                    "score": 0,
                    "matched_by": [],
                    "best_evidence": None,
                }
            ],
            "algorithm_version": "requirement-v1",
        }
    )

    TailoringService._attach_tailoring_feedback(
        relevance,
        [
            ReportGapChange(
                operation="report_gap",
                requirement_id="req-python",
                requirement="Python",
                reason="No supporting evidence was found.",
            )
        ],
    )

    assert relevance.requirements[0].tailoring_feedback == ["No supporting evidence was found."]


def test_tailoring_sqlite_timestamp_binding_uses_naive_utc():
    assert _db_utcnow().tzinfo is None


def test_fresh_tailoring_target_has_profile_identity_and_empty_library_sections():
    sections = fresh_tailoring_sections(
        "session-1",
        {"name": "Example User", "email": "user@example.com"},
    )

    assert [section["type"] for section in sections] == [
        "profile",
        "education",
        "skills",
        "experience",
        "languages",
        "certifications",
        "projects",
        "research",
    ]
    assert sections[0]["data"]["name"] == "Example User"
    assert sections[0]["data"]["summary"] == ""
    assert all(section["data"] == [] for section in sections[1:])
    assert all(section["id"].startswith("tailoring_session-1_") for section in sections)


def test_structural_section_changes_require_reason_and_evidence():
    with pytest.raises(ValidationError):
        _patch(
            [
                {
                    "operation": "create_section",
                    "section": {
                        "id": "highlights",
                        "type": "extras",
                        "title": "Highlights",
                        "data": [],
                    },
                }
            ]
        )

    patch = _patch(
        [
            {
                "operation": "create_section",
                "section": {
                    "id": "highlights",
                    "type": "extras",
                    "title": "Highlights",
                    "enabled": True,
                    "data": [],
                },
                "reason": "Surface a focused evidence-backed highlights section.",
                "evidence": [
                    {
                        "source": "cv",
                        "section_id": "experience",
                        "entry_id": "entry-1",
                        "field_path": "*",
                    }
                ],
            }
        ]
    )
    assert patch.changes[0].operation == "create_section"


def test_structural_section_operations_can_create_replace_remove_and_reorder():
    source = [
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Example User", "email": "user@example.com", "summary": ""},
        },
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "enabled": False,
            "data": [],
        },
        {
            "id": "education",
            "type": "education",
            "title": "Education",
            "enabled": False,
            "data": [],
        },
    ]
    proof = {
        "source": "cv",
        "section_id": "profile",
        "field_path": "*",
    }
    patch = _patch(
        [
            {
                "operation": "create_section",
                "section": {
                    "id": "highlights",
                    "type": "extras",
                    "title": "Highlights",
                    "data": [
                        {
                            "id": "highlight-1",
                            "title": "Selected work",
                            "fields": [{"label": "Evidence", "value": "Built dependable services."}],
                        }
                    ],
                },
                "reason": "Add a concise section for the strongest supported evidence.",
                "evidence": [proof],
            },
            {
                "operation": "replace_section",
                "section_id": "experience",
                "section": {
                    "id": "experience",
                    "type": "experience",
                    "title": "Selected Experience",
                    "enabled": True,
                    "data": [
                        {
                            "id": "experience-1",
                            "company": "Example Labs",
                            "position": "Engineer",
                            "description": "Built dependable services.",
                        }
                    ],
                },
                "reason": "Replace the empty scaffold with the relevant experience composition.",
                "evidence": [proof],
            },
            {
                "operation": "reorder_sections",
                "section_ids": ["profile", "highlights", "experience", "education"],
                "reason": "Put the most relevant evidence before education.",
                "evidence": [proof],
            },
            {
                "operation": "remove_section",
                "section_id": "education",
                "reason": "Omit an empty section to keep the document focused.",
                "evidence": [proof],
            },
        ]
    )

    updated, operations, _gaps = TailoringService._apply_patch(source, patch)

    assert operations == ["create_section", "replace_section", "reorder_sections", "remove_section"]
    assert [section["id"] for section in updated] == ["profile", "highlights", "experience"]
    assert updated[1]["type"] == "extras"
    assert updated[2]["title"] == "Selected Experience"


def test_structural_replacement_preserves_profile_identity():
    source = [
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "enabled": True,
            "data": {"name": "Example User", "email": "user@example.com", "summary": ""},
        }
    ]
    with pytest.raises(TailoringPatchError, match="identity"):
        TailoringService._apply_patch(
            source,
            _patch(
                [
                    {
                        "operation": "replace_section",
                        "section_id": "profile",
                        "section": {
                            "id": "profile",
                            "type": "profile",
                            "title": "Profile",
                            "data": {"name": "Invented User", "email": "user@example.com", "summary": ""},
                        },
                        "reason": "Attempted identity rewrite.",
                        "evidence": [
                            {"source": "cv", "section_id": "profile", "field_path": "*"}
                        ],
                    }
                ]
            ),
        )


def test_tailoring_status_contract_does_not_accept_capabilities():
    status = TailoringSessionStatusResponse.model_validate(
        {
            "protocol_version": 1,
            "session_id": "session-1",
            "application_id": "application-1",
            "cv_id": "cv-1",
            "status": "applied",
            "expires_at": "2026-08-30T20:00:00Z",
            "created_at": "2026-08-30T19:00:00Z",
            "exchanged_at": "2026-08-30T19:01:00Z",
            "submitted_at": "2026-08-30T19:02:00Z",
            "updated_at": "2026-08-30T19:02:00Z",
            "attempts": 1,
            "reported_gaps": [],
            "result": None,
        }
    )
    assert status.status == "applied"
    with pytest.raises(ValidationError):
        TailoringSessionStatusResponse.model_validate({**status.model_dump(mode="json"), "capability": "secret"})


def test_stored_requirements_are_read_without_extraction():
    requirements = _stored_requirements(
        SimpleNamespace(
            relevance={
                "requirements": [
                    {
                        "requirement": {
                            "id": "req-1",
                            "text": "Python",
                            "normalized": "python",
                            "type": "hard_skill",
                            "required": True,
                            "weight": 1.0,
                        }
                    }
                ]
            }
        )
    )
    assert [requirement.normalized for requirement in requirements] == ["python"]


def test_phase_one_patch_is_copy_on_write_and_rejects_rich_text():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "description": "Original"}],
        }
    ]
    patch = TailoringPatch.model_validate(
        {
            "protocol_version": 1,
            "base_revision": 1,
            "base_hash": "a" * 64,
            "changes": [
                {
                    "operation": "replace_description",
                    "section_id": "experience",
                    "entry_id": "entry-1",
                    "value": "Updated",
                }
            ],
        }
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    assert source[0]["data"][0]["description"] == "Original"
    assert updated[0]["data"][0]["description"] == "Updated"

    rich_text_source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "description": []}],
        }
    ]
    with pytest.raises(TailoringPatchError):
        TailoringService._apply_patch(rich_text_source, patch)

    rich_text_patch = _patch(
        [
            {
                "operation": "replace_rich_text",
                "section_id": "experience",
                "entry_id": "entry-1",
                "field": "description",
                "value": "Updated through the skill protocol.",
            }
        ]
    )
    rich_text_updated, operations, _gaps = TailoringService._apply_patch(source, rich_text_patch)
    assert operations == ["replace_rich_text"]
    assert rich_text_updated[0]["data"][0]["description"] == "Updated through the skill protocol."


def _patch(changes):
    return TailoringPatch.model_validate(
        {
            "protocol_version": 1,
            "base_revision": 1,
            "base_hash": "a" * 64,
            "changes": changes,
        }
    )


def _rich_text_source():
    return [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "enabled": True,
            "data": [
                {
                    "id": "entry-1",
                    "company": "Example Labs",
                    "description": [
                        {
                            "id": "block-1",
                            "type": "bullet_list",
                            "items": [
                                {"id": "item-1", "text": "Built APIs."},
                                {"id": "item-2", "text": "Added monitoring."},
                            ],
                        },
                        {
                            "id": "block-2",
                            "type": "paragraph",
                            "items": [{"id": "item-3", "text": "Platform work."}],
                        },
                    ],
                },
            ],
        },
    ]


def test_phase_two_rich_text_and_bullet_operations_use_stable_ids():
    source = _rich_text_source()
    evidence = {
        "source": "cv",
        "section_id": "experience",
        "entry_id": "entry-1",
        "field_path": "description",
    }
    rewritten = _patch(
        [
            {
                "operation": "rewrite_rich_text",
                "section_id": "experience",
                "entry_id": "entry-1",
                "field": "description",
                "value": [
                    {
                        "id": "block-1",
                        "type": "bullet_list",
                        "items": [{"id": "item-1", "text": "Built dependable APIs."}],
                    }
                ],
                "evidence": [evidence],
            }
        ]
    )
    updated, operations, _gaps = TailoringService._apply_patch(source, rewritten)
    assert operations == ["rewrite_rich_text"]
    assert updated[0]["data"][0]["description"][0]["items"][0]["text"] == "Built dependable APIs."
    assert source[0]["data"][0]["description"][0]["items"][0]["text"] == "Built APIs."

    with pytest.raises(TailoringPatchError):
        TailoringService._apply_patch(
            source,
            _patch(
                [
                    {
                        "operation": "rewrite_rich_text",
                        "section_id": "experience",
                        "entry_id": "entry-1",
                        "field": "description",
                        "value": [
                            {
                                "id": "block-1",
                                "type": "bullet_list",
                                "items": [
                                    {"id": "item-1", "text": "Built APIs.", "style": {"bold": True}},
                                    {"id": "item-2", "text": "Added monitoring."},
                                ],
                            },
                            {"id": "block-2", "type": "paragraph", "items": [{"id": "item-3", "text": "Platform work."}]},
                        ],
                        "evidence": [evidence],
                    }
                ]
            ),
        )

    removed, _operations, _gaps = TailoringService._apply_patch(
        source,
        _patch(
            [
                {
                    "operation": "remove_bullet",
                    "section_id": "experience",
                    "entry_id": "entry-1",
                    "field": "description",
                    "block_id": "block-1",
                    "item_id": "item-2",
                }
            ]
        ),
    )
    assert [item["id"] for item in removed[0]["data"][0]["description"][0]["items"]] == ["item-1"]

    reordered, _operations, _gaps = TailoringService._apply_patch(
        source,
        _patch(
            [
                {
                    "operation": "reorder_bullets",
                    "section_id": "experience",
                    "entry_id": "entry-1",
                    "field": "description",
                    "block_id": "block-1",
                    "item_ids": ["item-2", "item-1"],
                }
            ]
        ),
    )
    assert [item["id"] for item in reordered[0]["data"][0]["description"][0]["items"]] == ["item-2", "item-1"]


def test_rich_text_rewrite_can_add_evidence_backed_plain_blocks_and_items():
    source = _rich_text_source()
    rewritten = _patch(
        [
            {
                "operation": "rewrite_rich_text",
                "section_id": "experience",
                "entry_id": "entry-1",
                "field": "description",
                "value": [
                    {
                        "id": "block-1",
                        "type": "bullet_list",
                        "items": [
                            {"id": "item-1", "text": "Built dependable APIs."},
                            {"id": "item-new", "text": "Improved service reliability."},
                        ],
                    },
                    {
                        "id": "block-new",
                        "type": "paragraph",
                        "items": [{"id": "item-new-block", "text": "Platform work."}],
                    },
                ],
                "evidence": [
                    {
                        "source": "cv",
                        "section_id": "experience",
                        "entry_id": "entry-1",
                        "field_path": "description",
                    }
                ],
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, rewritten)
    assert [block["id"] for block in updated[0]["data"][0]["description"]] == ["block-1", "block-new"]
    assert [item["id"] for item in updated[0]["data"][0]["description"][0]["items"]] == [
        "item-1",
        "item-new",
    ]


def test_phase_two_profile_bullet_operations_do_not_require_an_entry_id():
    source = [
        {
            "id": "profile",
            "type": "profile",
            "title": "Profile",
            "data": {
                "summary": [
                    {
                        "id": "summary-block",
                        "type": "bullet_list",
                        "items": [
                            {"id": "summary-item-1", "text": "First"},
                            {"id": "summary-item-2", "text": "Second"},
                        ],
                    }
                ]
            },
        }
    ]
    reordered, _operations, _gaps = TailoringService._apply_patch(
        source,
        _patch(
            [
                {
                    "operation": "reorder_bullets",
                    "section_id": "profile",
                    "field": "summary",
                    "block_id": "summary-block",
                    "item_ids": ["summary-item-2", "summary-item-1"],
                }
            ]
        ),
    )
    assert [item["id"] for item in reordered[0]["data"]["summary"][0]["items"]] == [
        "summary-item-2",
        "summary-item-1",
    ]


def test_phase_two_entry_operations_require_exact_id_permutations():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [
                {"id": "entry-1", "company": "One"},
                {"id": "entry-2", "company": "Two"},
            ],
        }
    ]
    updated, _operations, _gaps = TailoringService._apply_patch(
        source,
        _patch(
            [
                {
                    "operation": "reorder_entries",
                    "section_id": "experience",
                    "entry_ids": ["entry-2", "entry-1"],
                }
            ]
        ),
    )
    assert [entry["id"] for entry in updated[0]["data"]] == ["entry-2", "entry-1"]

    with pytest.raises(TailoringPatchError):
        TailoringService._apply_patch(
            source,
            _patch(
                [
                    {
                        "operation": "reorder_entries",
                        "section_id": "experience",
                        "entry_ids": ["entry-1"],
                    }
                ]
            ),
        )

    removed, _operations, _gaps = TailoringService._apply_patch(
        source,
        _patch(
            [{"operation": "remove_entry", "section_id": "experience", "entry_id": "entry-2"}]
        ),
    )
    assert [entry["id"] for entry in removed[0]["data"]] == ["entry-1"]


def test_phase_two_library_addition_copies_server_authoritative_row():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "enabled": False,
            "data": [],
        }
    ]
    patch = _patch(
        [
            {
                "operation": "add_library_entry",
                "section_id": "experience",
                "library_entry_id": "library-1",
                "source_row_id": "library-row-1",
                "evidence": [
                    {
                        "source": "library",
                        "library_entry_id": "library-1",
                        "source_row_id": "library-row-1",
                        "source_hash": "b" * 64,
                        "field_path": "description",
                    }
                ],
            }
        ]
    )
    updated, operations, _gaps = TailoringService._apply_patch(
        source,
        patch,
        {
            ("library-1", "library-row-1"): {
                "kind": "experience",
                "row": {
                    "id": "library-row-1",
                    "company": "Authoritative Labs",
                    "description": "Built supported systems.",
                },
            }
        },
    )
    assert operations == ["add_library_entry"]
    added = updated[0]["data"][0]
    assert added["company"] == "Authoritative Labs"
    assert added["id"] != "library-row-1"
    assert updated[0]["enabled"] is True
    assert source[0]["data"] == []


def test_library_addition_can_be_followed_by_a_prose_rewrite_of_the_copy():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [],
        }
    ]
    patch = _patch(
        [
            {
                "operation": "add_library_entry",
                "section_id": "experience",
                "entry_id": "tailored-entry-1",
                "library_entry_id": "library-1",
                "source_row_id": "library-row-1",
                "evidence": [
                    {
                        "source": "library",
                        "library_entry_id": "library-1",
                        "source_row_id": "library-row-1",
                        "source_hash": "b" * 64,
                        "field_path": "description",
                    }
                ],
            },
            {
                "operation": "replace_rich_text",
                "section_id": "experience",
                "entry_id": "tailored-entry-1",
                "field": "description",
                "value": "Built dependable platform systems.",
            },
        ]
    )
    updated, operations, _gaps = TailoringService._apply_patch(
        source,
        patch,
        {
            ("library-1", "library-row-1"): {
                "kind": "experience",
                "row": {
                    "id": "library-row-1",
                    "company": "Authoritative Labs",
                    "description": "Built supported systems.",
                },
            }
        },
    )
    assert operations == ["add_library_entry", "replace_rich_text"]
    assert updated[0]["data"][0] == {
        "id": "tailored-entry-1",
        "company": "Authoritative Labs",
        "description": "Built dependable platform systems.",
    }


def test_phase_two_policy_rejects_protected_field_mutation():
    before = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "company": "Original Labs", "description": "Text"}],
        }
    ]
    after = [
        {
            **before[0],
            "data": [{"id": "entry-1", "company": "Invented Labs", "description": "Text"}],
        }
    ]
    with pytest.raises(TailoringPolicyError):
        validate_document_delta(
            before,
            after,
            [
                SimpleNamespace(
                    operation="rewrite_rich_text",
                    section_id="experience",
                    entry_id="entry-1",
                    field="description",
                )
            ],
        )


def test_server_fact_guard_rejects_new_numeric_claims_in_rewritten_prose():
    source = _rich_text_source()
    patch = _patch(
        [
            {
                "operation": "rewrite_rich_text",
                "section_id": "experience",
                "entry_id": "entry-1",
                "field": "description",
                "value": [
                    {
                        "id": "block-1",
                        "type": "bullet_list",
                        "items": [
                            {"id": "item-1", "text": "Improved API performance by 47%."},
                            {"id": "item-2", "text": "Added monitoring."},
                        ],
                    },
                    {"id": "block-2", "type": "paragraph", "items": [{"id": "item-3", "text": "Platform work."}]},
                ],
                "evidence": [
                    {
                        "source": "cv",
                        "section_id": "experience",
                        "entry_id": "entry-1",
                        "field_path": "description",
                    }
                ],
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    with pytest.raises(TailoringFactError, match="47%"):
        validate_tailoring_facts(source, updated, patch.changes, [])


def test_server_fact_guard_does_not_borrow_a_number_from_another_cv_entry():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [
                {"id": "job-a", "description": "Improved API performance."},
                {"id": "job-b", "description": "Reduced latency by 32%."},
            ],
        }
    ]
    patch = _patch(
        [
            {
                "operation": "replace_description",
                "section_id": "experience",
                "entry_id": "job-a",
                "value": "Improved API performance by 32%.",
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    with pytest.raises(TailoringFactError, match="32%"):
        validate_tailoring_facts(source, updated, patch.changes, [])


def test_server_fact_guard_accepts_new_claims_from_a_web_citation():
    source = [
        {
            "id": "experience",
            "type": "experience",
            "title": "Experience",
            "data": [{"id": "entry-1", "description": "Built API services."}],
        }
    ]
    patch = _patch(
        [
            {
                "operation": "replace_rich_text",
                "section_id": "experience",
                "entry_id": "entry-1",
                "field": "description",
                "value": "Built Python API services with a 47% improvement.",
                "evidence": [
                    {
                        "source": "web",
                        "url": "https://example.com/technical-guide",
                        "title": "Technical guide",
                        "excerpt": "Python services can report a 47% improvement in this contextual example.",
                    }
                ],
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    validate_tailoring_facts(source, updated, patch.changes, [])


def test_server_fact_guard_can_check_a_rewrite_of_a_new_library_copy():
    library_entry = LibraryEntry(
        id="library-1",
        library_id="library",
        kind="experience",
        payload=[{"id": "library-row-1", "description": "Built API services."}],
    )
    source_hash = library_entry_content_hash(library_entry)
    source = [{"id": "experience", "type": "experience", "title": "Experience", "data": []}]
    patch = _patch(
        [
            {
                "operation": "add_library_entry",
                "section_id": "experience",
                "entry_id": "tailored-entry-1",
                "library_entry_id": "library-1",
                "source_row_id": "library-row-1",
                "evidence": [
                    {
                        "source": "library",
                        "library_entry_id": "library-1",
                        "source_row_id": "library-row-1",
                        "source_hash": source_hash,
                        "field_path": "description",
                    }
                ],
            },
            {
                "operation": "replace_rich_text",
                "section_id": "experience",
                "entry_id": "tailored-entry-1",
                "field": "description",
                "value": "Built Python API services with a 47% improvement.",
                "evidence": [
                    {
                        "source": "library",
                        "library_entry_id": "library-1",
                        "source_row_id": "library-row-1",
                        "source_hash": source_hash,
                        "field_path": "description",
                    },
                    {
                        "source": "web",
                        "url": "https://example.com/technical-guide",
                        "title": "Technical guide",
                        "excerpt": "Python services can report a 47% improvement in this contextual example.",
                    },
                ],
            },
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(
        source,
        patch,
        {
            ("library-1", "library-row-1"): {
                "kind": "experience",
                "row": {"id": "library-row-1", "description": "Built API services."},
            }
        },
    )
    validate_tailoring_facts(source, updated, patch.changes, [library_entry])


def test_structural_fact_guard_requires_personal_evidence_for_new_identity_fields():
    source = [{"id": "experience", "type": "experience", "title": "Experience", "data": []}]
    patch = _patch(
        [
            {
                "operation": "create_section",
                "section": {
                    "id": "selected-experience",
                    "type": "experience",
                    "title": "Selected Experience",
                    "data": [
                        {
                            "id": "entry-1",
                            "company": "Invented Labs",
                            "position": "Engineer",
                            "description": "Built useful services.",
                        }
                    ],
                },
                "reason": "Add a role selected for the application.",
                "evidence": [
                    {
                        "source": "web",
                        "url": "https://example.com/context",
                        "title": "Context",
                        "excerpt": "A contextual description of engineering work.",
                    }
                ],
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(source, patch)
    with pytest.raises(TailoringFactError, match="Structured field"):
        validate_tailoring_section_facts(source, updated, patch.changes, [])


def test_structural_fact_guard_accepts_a_new_role_backed_by_a_cv_row():
    target_before = [{"id": "experience", "type": "experience", "title": "Experience", "data": []}]
    source_evidence = [
        {
            "id": "source-experience",
            "type": "experience",
            "title": "Experience",
            "data": [
                {
                    "id": "source-entry",
                    "company": "Example Labs",
                    "position": "Engineer",
                    "description": "Built Python services.",
                }
            ],
        }
    ]
    patch = _patch(
        [
            {
                "operation": "create_section",
                "section": {
                    "id": "selected-experience",
                    "type": "experience",
                    "title": "Selected Experience",
                    "data": [
                        {
                            "id": "entry-1",
                            "company": "Example Labs",
                            "position": "Engineer",
                            "description": "Built Python services.",
                        }
                    ],
                },
                "reason": "Bring the directly supported role into the tailored document.",
                "evidence": [
                    {
                        "source": "cv",
                        "section_id": "source-experience",
                        "entry_id": "source-entry",
                        "field_path": "*",
                    }
                ],
            }
        ]
    )
    updated, _operations, _gaps = TailoringService._apply_patch(target_before, patch)
    validate_tailoring_section_facts(
        target_before,
        updated,
        patch.changes,
        [],
        evidence_sections=source_evidence,
    )
