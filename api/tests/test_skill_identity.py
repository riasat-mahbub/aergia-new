import pytest

from app.scanner.skills import canonicalize_skill, extract_skills, find_skill


@pytest.mark.parametrize("labels", [
    ("Git", "git"), ("Postgres", "PostgreSQL"), ("k8s", "Kubernetes"),
    ("React.js", "React"), ("JS", "JavaScript"),
])
def test_identity_aliases_are_stable(labels: tuple[str, str]) -> None:
    first, second = labels
    assert canonicalize_skill(first) == canonicalize_skill(second)
    assert canonicalize_skill(first) == canonicalize_skill(first)
    assert canonicalize_skill(first.upper()) == canonicalize_skill(first)


def test_unknown_exact_identity_survives_extraction() -> None:
    assert canonicalize_skill("Fabrikam-SDK") == "fabrikam-sdk"
    assert "fabrikam-sdk" in extract_skills("Built with Fabrikam-SDK", target_terms=["Fabrikam-SDK"])
    assert "fabrikam-sdk" not in extract_skills("Built with Other-SDK", target_terms=["Fabrikam-SDK"])


@pytest.mark.parametrize("left,right", [
    ("cloud", "AWS"), ("containers", "Docker"), ("DevOps", "GitHub Actions"),
    ("consulting", "client-facing"), ("Docker", "Kubernetes"),
])
def test_semantic_relationships_are_not_identities(left: str, right: str) -> None:
    assert canonicalize_skill(left) != canonicalize_skill(right)


@pytest.mark.parametrize("target,text", [
    ("Java", "JavaScript"), ("C", "C++"), ("C", "C#"),
    ("C++", "C#"), ("C#", "C++"), ("R", "Bar"),
    ("Go", "we go to market"),
])
def test_token_collisions_do_not_match(target: str, text: str) -> None:
    assert find_skill(text, target) is None


@pytest.mark.parametrize("target,text", [
    ("C++", "Built C++ tools"), ("C#", "Built C# tools"),
    (".NET", "Built .NET services"), ("Go", "Built services in Go"),
    ("R", "Analyzed data in R"),
])
def test_punctuation_and_short_language_names_match(target: str, text: str) -> None:
    assert find_skill(text, target) is not None
