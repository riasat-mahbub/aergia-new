import hashlib
import json
from pathlib import Path

from app.scanner.requirements import RequirementSource


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "scanner" / "alayacare"


def _fixture() -> tuple[dict[str, object], str, str]:
    annotations = json.loads((FIXTURE_DIR / "annotations.json").read_text(encoding="utf-8"))
    job_description = (FIXTURE_DIR / "job_description.txt").read_text(encoding="utf-8")
    cv_text = (FIXTURE_DIR / "cv_text_redacted.txt").read_text(encoding="utf-8")
    return annotations, job_description, cv_text


def test_alayacare_fixture_sources_are_frozen_and_redacted() -> None:
    annotations, job_description, cv_text = _fixture()
    source = annotations["source"]

    assert hashlib.sha256(job_description.encode("utf-8")).hexdigest() == source[
        "job_description_sha256"
    ]
    assert hashlib.sha256(cv_text.encode("utf-8")).hexdigest() == source[
        "cv_redacted_text_sha256"
    ]
    assert source["cv_source_pdf_sha256"] == "baa46c978e9f9e96f7b8b755ab71c93ef1018c21c9b46587af53027597639880"
    assert "[REDACTED NAME]" in cv_text
    assert "[REDACTED EMAIL]" in cv_text
    assert "[REDACTED PHONE]" in cv_text
    assert "[REDACTED URL]" in cv_text
    assert "@" not in cv_text
    assert "http://" not in cv_text
    assert "https://" not in cv_text


def test_alayacare_annotations_resolve_to_exact_source_spans() -> None:
    annotations, job_description, _ = _fixture()

    for section in annotations["section_annotations"]:
        assert section["heading"] in job_description

    items = [
        *annotations["expected_non_requirements"],
        *annotations["requirements"],
        *annotations["separate_logistics"],
    ]
    for item in items:
        original_text = item["source_text"]
        source_start = job_description.index(original_text)
        source_end = source_start + len(original_text)
        source = RequirementSource(
            original_text=original_text,
            source_start=source_start,
            source_end=source_end,
            extraction_confidence=1.0,
            extractor_version="alayacare-fixture-v1",
        )
        assert job_description[source.source_start : source.source_end] == source.original_text


def test_alayacare_core_expected_labels_are_explicit() -> None:
    annotations, _, _ = _fixture()
    requirements = {item["id"]: item for item in annotations["requirements"]}

    asset_requirement = requirements["french-english"]
    assert asset_requirement["importance"] == "preferred"

    compound = requirements["modern-development-practices"]
    assert compound["mandatory_components_supported"] == 2
    assert compound["mandatory_components_partial"] == 1
    assert compound["mandatory_components_total"] == 4
    assert compound["components"][-1] == {
        "concept": "monitoring",
        "cv_evidence": "not_evidenced",
    }

    curiosity = requirements["industry-trends-curiosity"]["cv_evidence"]
    assert curiosity["software_development_concept"] == "supported"
    assert curiosity["curiosity_about_current_trends_expectation"] == "not_evidenced"
    assert curiosity["must_not_be_fully_supported"] is True

    exclusions = {item["reason"] for item in annotations["expected_non_requirements"]}
    assert "employer_information" in exclusions
    assert "application_process" in exclusions
    assert "legal_or_application_process" in exclusions
