"""Pure keyword extraction, Library matching, and relevance contracts."""

import pytest

from app.services.relevance import (
    ALGORITHM_VERSION,
    ENTRY_RELEVANCE_THRESHOLD,
    KEYWORD_EXTRACTION_ERROR,
    KeywordExtractionError,
    calculate_relevance,
    extract_keywords,
    flatten_library_fields,
    normalize_text,
    score_skill_items,
    score_library_rows,
    select_relevant_library_rows,
    tokenize,
)


def test_normalization_and_technical_token_boundaries():
    assert normalize_text("  Node.js\u2014CI/CD  ") == "node.js-ci/cd"
    assert tokenize("C, C++, C#, .NET, Node.js, CI/CD, Go, SQL Server, R") == [
        "c",
        "c++",
        "c#",
        ".net",
        "node.js",
        "ci/cd",
        "go",
        "sql",
        "server",
        "r",
    ]


def test_one_character_candidates_require_uppercase_source_spelling():
    keywords = extract_keywords("", "x\nC\nR\nr")
    normalized = {keyword.normalized for keyword in keywords}
    assert "c" in normalized
    assert "r" in normalized
    assert "x" not in normalized


def test_role_required_and_preferred_weighting_is_deterministic():
    keywords = extract_keywords("Python", "Requirements:\nPython\nPreferred:\nPython")
    python = next(keyword for keyword in keywords if keyword.normalized == "python")
    assert python.weight == pytest.approx(1 + 2**0.0 * 0 + 1.584962500721156 + 2 + 1 + 0.5)


def test_phrase_containment_dedupes_lower_or_equal_weight_terms():
    keywords = extract_keywords("", "distributed systems")
    normalized = {keyword.normalized for keyword in keywords}
    assert "distributed systems" in normalized
    assert "distributed" not in normalized
    assert "systems" not in normalized


def test_extraction_rejects_stopword_only_text_with_exact_error():
    with pytest.raises(KeywordExtractionError, match=KEYWORD_EXTRACTION_ERROR):
        extract_keywords("", "the and with requirements")


def test_library_flattening_keeps_relevant_rich_text_and_excludes_metadata():
    fields = flatten_library_fields(
        [
            {
                "id": "library-1",
                "kind": "experience",
                "payload": [
                    {
                        "id": "row-1",
                        "company": "Example Labs",
                        "position": "Platform Engineer",
                        "description": {"root": {"children": [{"children": [{"text": "Python systems"}]}]}},
                        "start_date": "2020",
                        "url": "https://example.com",
                    }
                ],
            }
        ]
    )
    text = " ".join(field.text for field in fields)
    assert "Example Labs" in text
    assert "Python systems" in text
    assert "2020" not in text
    assert "example.com" not in text
    assert all(field.library_entry_id == "library-1" for field in fields)


def test_kind_threshold_uses_positive_kind_maximum_and_stable_order():
    keywords = [
        {"text": "Python", "normalized": "python", "weight": 10},
        {"text": "FastAPI", "normalized": "fastapi", "weight": 3},
    ]
    entries = [
        {"id": "lib", "kind": "skill", "payload": [{"id": "first", "category": "Python"}, {"id": "second", "category": "FastAPI"}]}
    ]
    scored = score_library_rows(keywords, entries)
    assert [row.source_row_id for row in scored] == ["first", "second"]
    assert scored[0].normalized_score == pytest.approx(1)
    assert scored[1].normalized_score == pytest.approx(0.3)
    selected = select_relevant_library_rows(keywords, entries)
    assert [row.source_row_id for row in selected] == ["first"]
    assert ENTRY_RELEVANCE_THRESHOLD == 0.35


def test_skill_items_are_scored_independently_for_fit_trimming():
    row = score_library_rows(
        [{"text": "Python", "normalized": "python", "weight": 4}],
        [{"id": "lib", "kind": "skill", "payload": [{"id": "row", "category": "Backend", "items": ["Legacy", "Python"]}]}],
    )[0]

    scored = score_skill_items([{"text": "Python", "normalized": "python", "weight": 4}], row)

    assert [(item.text, item.score) for item in scored] == [("Legacy", 0), ("Python", 4)]


def test_relevance_is_weighted_coverage_with_complete_evidence():
    keywords = [
        {"text": "Python", "normalized": "python", "weight": 3},
        {"text": "FastAPI", "normalized": "fastapi", "weight": 1},
        {"text": "Rust", "normalized": "rust", "weight": 2},
    ]
    result = calculate_relevance(
        keywords,
        [
            {
                "type": "experience",
                "data": [{"id": "row-1", "company": "Example", "description": "Python"}],
            },
            {"type": "profile", "data": {"title": "FastAPI specialist", "summary": "Reliable services"}},
        ],
    )
    assert result.score == 67
    assert result.matched_keywords == ["Python", "FastAPI"]
    assert result.missing_keywords == ["Rust"]
    assert {e.keyword for e in result.evidence} == {"Python", "FastAPI"}
    assert result.algorithm_version == ALGORITHM_VERSION
