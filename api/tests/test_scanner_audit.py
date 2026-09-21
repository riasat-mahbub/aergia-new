from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.scanner.audit import build_scanner_audit, format_scanner_audit


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "scanner" / "audit" / "shadow_results.json"


def test_audit_aggregates_only_current_scanner_results_and_lists_review_ids() -> None:
    records = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    report = build_scanner_audit(records, total_applications=4)

    assert report["applications"] == {
        "total": 4,
        "with_scanner_result": 3,
        "current_scanner_results": 2,
        "stale_scanner_results": 1,
        "without_scanner_result": 1,
    }
    assert report["job_fit"]["min"] == 0.4
    assert report["job_fit"]["median"] == pytest.approx(0.6)
    assert report["job_fit"]["mean"] == pytest.approx(0.6)
    assert report["job_fit"]["max"] == 0.8
    assert report["classified_fraction"]["min"] == 0.5
    assert report["classified_fraction"]["median"] == pytest.approx(0.7)
    assert report["classified_fraction"]["mean"] == pytest.approx(0.7)
    assert report["classified_fraction"]["max"] == 0.9
    assert report["evidence_scorable_fraction"]["min"] == 0.8
    assert report["evidence_scorable_fraction"]["median"] == pytest.approx(0.9)
    assert report["evidence_scorable_fraction"]["mean"] == pytest.approx(0.9)
    assert report["evidence_scorable_fraction"]["max"] == 1.0
    assert report["requirement_counts"] == {
        "supported": 2,
        "partial": 3,
        "not_evidenced": 4,
        "conflicting": 1,
        "unverifiable": 1,
    }
    assert report["unverifiable_component_count"] == 3
    assert report["required_constraint_conflicts"] == 1
    assert report["lexical"]["term_counts"] == {
        "exact": 2,
        "normalized": 1,
        "variant": 1,
        "absent": 2,
    }
    assert report["pdf_status_counts"] == {"pass": 1, "warning": 1, "fail": 0, "unavailable": 0}
    assert report["freshness_reason_frequencies"] == {"job_changed": 1, "matcher_version_changed": 1}
    assert report["extraction_warning_frequencies"]["concept_spans_not_promoted"] == 2
    assert report["interesting_application_ids"]["highest_job_fit"][0]["application_id"] == "app-a"
    assert report["interesting_application_ids"]["lowest_classification_coverage"][0]["application_id"] == "app-b"
    assert report["interesting_application_ids"]["applications_with_conflicts"][0]["application_id"] == "app-b"

    readable = format_scanner_audit(report)
    assert "SCANNER SHADOW AUDIT" in readable
    assert "app-stale" not in readable
    assert "job_description" not in readable.lower()
    assert "cv contents" not in readable.lower()


def test_audit_report_does_not_copy_job_or_cv_content() -> None:
    source_text = "PRIVATE JD AND CV TEXT"
    record = {
        "application_id": "app-safe",
        "job_description": source_text,
        "cv_text": source_text,
        "freshness": {"current": True, "reasons": []},
        "scanner_result": {
            "schema_version": "scanner-v1",
            "versions": {},
            "requirement_extraction": {"warnings": []},
            "semantic": {"summary": {}, "requirements": []},
            "lexical": {"summary": {}, "terms": []},
            "pdf_recovery": {"status": "unavailable"},
        },
    }

    serialized = json.dumps(build_scanner_audit([record]))

    assert source_text not in serialized
