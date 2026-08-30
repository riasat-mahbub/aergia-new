"""Phase 1 protocol fixture checks against the server-side Pydantic contract."""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.tailoring import TailoringCodeExchange, TailoringEvidencePacket, TailoringPatch
from app.services.tailoring import TailoringPatchError, TailoringService, _stored_requirements
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
                }
            ],
        }
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
