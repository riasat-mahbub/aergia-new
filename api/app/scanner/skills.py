"""Shared identity vocabulary for technologies named by jobs and CVs.

Only spelling and product-name identities belong here. Behavioral and
umbrella relationships stay in the semantic matcher.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable

_DASHES = str.maketrans({char: "-" for char in "‐‑‒–—―−﹘﹣－"})

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"),
    "java": ("java",),
    "c": ("c",),
    "c#": ("c#", "c sharp", "csharp"),
    "c++": ("c++", "cpp"),
    ".net": (".net", "dotnet"),
    "go": ("go", "golang"),
    "r": ("r",),
    "rust": ("rust",),
    "ruby": ("ruby",),
    "php": ("php",),
    "kotlin": ("kotlin",),
    "swift": ("swift",),
    "scala": ("scala",),
    "react": ("react", "react.js", "reactjs"),
    "angular": ("angular",),
    "vue": ("vue", "vue.js", "vuejs"),
    "node.js": ("node.js", "nodejs"),
    "express": ("express", "express.js", "expressjs"),
    "fastapi": ("fastapi", "fast api"),
    "django": ("django",),
    "flask": ("flask",),
    "next.js": ("next.js", "nextjs"),
    "graphql": ("graphql",),
    "sql": ("sql",),
    "postgresql": ("postgresql", "postgres"),
    "mysql": ("mysql",),
    "sqlite": ("sqlite", "sqlite3"),
    "mongodb": ("mongodb",),
    "redis": ("redis",),
    "elasticsearch": ("elasticsearch",),
    "kafka": ("kafka", "apache kafka"),
    "spark": ("spark", "apache spark"),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure", "microsoft azure"),
    "gcp": ("gcp", "google cloud platform"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "terraform": ("terraform",),
    "git": ("git",),
    "linux": ("linux",),
    "github actions": ("github actions",),
    "jenkins": ("jenkins",),
    "power platform": ("power platform", "microsoft power platform"),
    "sharepoint": ("sharepoint", "microsoft sharepoint"),
    "microsoft 365": ("microsoft 365", "m365", "office 365"),
    "powershell": ("powershell",),
    "bash": ("bash",),
}


def _normalize(label: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", label).translate(_DASHES).casefold().split())


ALIAS_TO_SKILL = {
    _normalize(alias): canonical
    for canonical, aliases in SKILL_ALIASES.items()
    for alias in aliases
}


def canonicalize_skill(label: str) -> str:
    """Return one stable identity; unknown labels keep exact normalized form."""

    normalized = _normalize(label)
    return ALIAS_TO_SKILL.get(normalized, normalized)


def _surface(text: str, alias: str, *, skill_section: bool = False) -> str | None:
    # A punctuation-bearing language must consume its complete token. The
    # right boundary also prevents C from matching C++ or C#.
    escaped = re.escape(alias).replace(r"\ ", r"\s+")
    pattern = re.compile(rf"(?<![\w+#]){escaped}(?![\w+#])", re.I)
    normalized_text = unicodedata.normalize("NFKC", text).translate(_DASHES)
    for match in pattern.finditer(normalized_text):
        if alias in {"c", "r", "go"} and not skill_section:
            if match.group() != {"c": "C", "r": "R", "go": "Go"}[alias]:
                continue
            nearby = normalized_text[max(0, match.start() - 16) : min(len(normalized_text), match.end() + 16)]
            context_cue = re.search(
                r"\b(?:programming|language|developer|software|coding|skills?|experience|"
                r"proficiency|familiarity|using|written|built|developed|programmer|code|"
                r"services?|applications?|development|frameworks?|tools?|data|statistical)\b",
                nearby,
                re.I,
            )
            c_list = alias == "c" and re.search(r"\bC\s*[,/]\s*(?:C\+\+|C#)\b", nearby)
            if not context_cue and not c_list:
                continue
        return match.group()
    return None


def find_skill(text: str, label: str, *, skill_section: bool = False) -> str | None:
    """Find the target identity with safe boundaries, including unknown terms."""

    canonical = canonicalize_skill(label)
    aliases = SKILL_ALIASES.get(canonical, (label,))
    for alias in sorted(aliases, key=len, reverse=True):
        surface = _surface(text, alias, skill_section=skill_section)
        if surface is not None:
            return surface
    return None


def extract_skills(text: str, *, target_terms: Iterable[str] = (), skill_section: bool = False) -> set[str]:
    """Extract known skills plus exact target labels using the same rules."""

    terms = set(SKILL_ALIASES) | {canonicalize_skill(term) for term in target_terms if term.strip()}
    return {term for term in terms if find_skill(text, term, skill_section=skill_section) is not None}


def is_known_skill(label: str) -> bool:
    return canonicalize_skill(label) in SKILL_ALIASES


__all__ = ["SKILL_ALIASES", "canonicalize_skill", "extract_skills", "find_skill", "is_known_skill"]
