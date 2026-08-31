"""Phase 1 protocol fixture checks against the server-side Pydantic contract."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.tailoring import (
    TailoringCodeExchange,
    TailoringEvidencePacket,
    TailoringPatch,
    TailoringSessionStatusResponse,
)
from app.services.tailoring_facts import TailoringFactError, validate_tailoring_facts
from app.services.tailoring import (
    TailoringPatchError,
    TailoringService,
    _db_utcnow,
    _stored_requirements,
    build_tailoring_prompt,
)
from app.services.tailoring_policy import TailoringPolicyError, validate_document_delta


_FIXTURES = Path(__file__).parents[2] / "contracts" / "fixtures"


def test_valid_tailoring_patch_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "tailoring-patch.valid.json").read_text())
    patch = TailoringPatch.model_validate(payload)
    assert patch.protocol_version == 1
    assert [change.operation for change in patch.changes] == ["replace_description", "report_gap"]


def test_valid_evidence_fixture_matches_protocol():
    payload = json.loads((_FIXTURES / "evidence-packet.valid.json").read_text())
    evidence = TailoringEvidencePacket.model_validate(payload)
    assert evidence.protocol_version == 1
    assert evidence.cv.id == "cv-1"
    assert evidence.protected_facts["profile"]["name"] == "Example User"


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
    prompt = build_tailoring_prompt("https://aergia.example/agent/tailor/session-1", "code-1234567890123456")
    assert "https://aergia.example/agent/tailor/session-1" in prompt
    assert "One-time session code: code-1234567890123456" in prompt
    assert "ask for approval" in prompt


def test_tailoring_sqlite_timestamp_binding_uses_naive_utc():
    assert _db_utcnow().tzinfo is None


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
    assert source[0]["data"] == []


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
