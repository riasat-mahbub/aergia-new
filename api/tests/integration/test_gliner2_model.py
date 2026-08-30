"""Opt-in real-model checks for manually annotated job descriptions."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.mark.integration
def test_real_gliner2_small_against_operator_fixture() -> None:
    if os.environ.get("RUN_GLINER2_INTEGRATION") != "1":
        pytest.skip("set RUN_GLINER2_INTEGRATION=1 to run the real model suite")
    fixture_name = os.environ.get("GLINER2_EVAL_FIXTURES")
    if not fixture_name:
        pytest.skip("set GLINER2_EVAL_FIXTURES to a manually annotated fixture")
    pytest.importorskip("gliner2")

    from scripts.gliner2_evaluate import _evaluate_case, _read_cases
    from app.services.requirement_extractor import Gliner2RequirementExtractor

    cases = _read_cases(Path(fixture_name))
    assert cases, "the evaluation fixture must contain at least one job description"
    extractor = Gliner2RequirementExtractor()
    for case in cases:
        assert case.get("expected"), f"case {case['id']} has no manual annotations"
        result = extractor.extract_result(str(case.get("role", "")), case["text"])
        evaluation = _evaluate_case(case, result)
        assert evaluation["false_required_count"] == 0, evaluation["false_required"]
