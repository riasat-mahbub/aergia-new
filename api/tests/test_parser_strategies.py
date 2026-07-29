"""Strategy seam tests.

Locks:

- ``RegexStrategy`` works against a synthetic ``ExtractedDocument`` and
  produces ``list[SectionInstance]`` + ``ConfidenceReport``;
- ``LLMStrategy`` raises ``NotImplementedError`` with a message that names
  the LLM seam — proves the deferred stub is wired in the public surface;
- both strategies satisfy the :class:`ParseStrategy` protocol surface.
"""

from __future__ import annotations

import pytest

from app.schema.models import SectionInstance
from app.services.parser.schemas import ConfidenceReport, ExtractedDocument
from app.services.parser.strategies import LLMStrategy, RegexStrategy


def _empty_extracted() -> ExtractedDocument:
    return ExtractedDocument(
        blocks=[],
        plain_text="",
        columns=[],
        source_format="pdf",
    )


def test_regex_strategy_returns_typed_tuple():
    s = RegexStrategy()
    sections, conf = s.structure(_empty_extracted())
    assert isinstance(sections, list)
    assert isinstance(conf, ConfidenceReport)
    assert all(isinstance(x, SectionInstance) for x in sections)


def test_regex_strategy_named_regex():
    assert RegexStrategy.name == "regex"


def test_llm_strategy_raises_not_implemented():
    s = LLMStrategy()
    with pytest.raises(NotImplementedError) as exc_info:
        s.structure(_empty_extracted())
    assert "LLM" in str(exc_info.value)


def test_llm_strategy_named_llm():
    assert LLMStrategy.name == "llm"


def test_both_strategies_have_structure_method():
    """Type-level protocol surface — kept simple for v1 since duck typing
    via ``strategy.structure(...)`` is what the orchestrator actually
    exercises; this test just guards the public API from accidentally
    renaming the entry point."""
    for strategy_cls in (RegexStrategy, LLMStrategy):
        assert callable(getattr(strategy_cls, "structure", None))
