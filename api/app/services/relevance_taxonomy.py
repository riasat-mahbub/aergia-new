"""Small, reviewable taxonomy used by the requirement relevance baseline.

The taxonomy is deliberately data, not inference.  Adding an alias should be
safe to review in a code change and makes a match more transparent than a
large language model or an embedding index would be.
"""

from __future__ import annotations


# Canonical names are the values persisted in requirement explanations.  The
# aliases cover common spelling, punctuation, and product-name variants only;
# they are not intended to be a general thesaurus.
HARD_SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "python": ("python",),
    "javascript": ("javascript", "js"),
    "typescript": ("typescript", "ts"),
    "java": ("java",),
    "c#": ("c#", "c sharp", "csharp"),
    ".net": (".net", "dotnet", "asp.net", "asp net"),
    "c++": ("c++", "cpp"),
    "go": ("go", "golang"),
    "rust": ("rust",),
    "ruby": ("ruby",),
    "php": ("php",),
    "kotlin": ("kotlin",),
    "swift": ("swift",),
    "scala": ("scala",),
    "react": ("react", "react.js", "reactjs"),
    "angular": ("angular",),
    "vue": ("vue", "vue.js", "vuejs"),
    "node.js": ("node.js", "nodejs", "node"),
    "express": ("express", "express.js", "expressjs"),
    "fastapi": ("fastapi", "fast api"),
    "django": ("django",),
    "flask": ("flask",),
    "spring": ("spring", "spring boot", "spring framework"),
    "next.js": ("next.js", "nextjs", "next"),
    "graphql": ("graphql", "graph ql"),
    "sql": ("sql",),
    "postgresql": ("postgresql", "postgres", "postgre sql"),
    "mysql": ("mysql", "my sql"),
    "sqlite": ("sqlite", "sqlite3"),
    "mongodb": ("mongodb", "mongo db", "mongo"),
    "redis": ("redis",),
    "elasticsearch": ("elasticsearch", "elastic search"),
    "kafka": ("kafka", "apache kafka"),
    "spark": ("spark", "apache spark"),
    "pandas": ("pandas",),
    "numpy": ("numpy",),
    "aws": ("aws", "amazon web services"),
    "azure": ("azure", "microsoft azure"),
    "gcp": ("gcp", "google cloud", "google cloud platform"),
    "docker": ("docker",),
    "kubernetes": ("kubernetes", "k8s"),
    "terraform": ("terraform",),
    "git": ("git",),
    "linux": ("linux",),
    "rest api": ("rest api", "restful api", "rest apis", "restful apis", "rest"),
    "ci/cd": ("ci/cd", "ci cd", "continuous integration", "continuous delivery", "continuous deployment"),
    "github actions": ("github actions",),
    "jenkins": ("jenkins",),
    "microservices": ("microservices", "micro services"),
    "distributed systems": ("distributed systems", "distributed system"),
    "cloud native": ("cloud native", "cloud-native"),
    "system design": ("system design", "systems design"),
    "data structures": ("data structures", "data structure"),
    "algorithms": ("algorithms", "algorithm"),
    "object-oriented programming": ("object-oriented programming", "object oriented programming", "oop"),
    "unit testing": ("unit testing", "unit tests", "unit test"),
    "integration testing": ("integration testing", "integration tests", "integration test"),
    "test automation": ("test automation", "automated testing"),
    "security": ("security", "cybersecurity", "cyber security"),
    "performance optimization": ("performance optimization", "performance tuning", "optimization"),
}

RESPONSIBILITY_ALIASES: dict[str, tuple[str, ...]] = {
    "research": ("research",),
    "software development": ("software development", "software engineer", "software engineering"),
    "backend development": ("backend development", "back-end development", "backend engineering"),
    "frontend development": ("frontend development", "front-end development", "frontend engineering"),
    "full-stack development": ("full-stack development", "full stack development", "fullstack development"),
    "api development": ("api development", "API design", "API integration"),
    "architecture": ("architecture", "architectural design"),
    "project management": ("project management", "manage projects", "project manager"),
    "technical leadership": ("technical leadership", "technical lead", "tech lead"),
    "team leadership": ("team leadership", "lead a team", "leading a team"),
    "mentoring": ("mentoring", "mentor", "coaching"),
    "stakeholder management": ("stakeholder management", "stakeholder communication"),
    "communication": ("communication", "communicate", "written communication"),
    "documentation": ("documentation", "technical documentation", "documenting"),
    "code review": ("code review", "code reviews", "review code"),
    "debugging": ("debugging", "debug", "troubleshooting"),
    "collaboration": ("collaboration", "collaborate", "cross-functional"),
    "agile": ("agile", "agile methodology"),
    "scrum": ("scrum",),
    "kanban": ("kanban",),
}

CERTIFICATION_ALIASES: dict[str, tuple[str, ...]] = {
    "ccna": ("ccna",),
    "ccnp": ("ccnp",),
    "ccie": ("ccie",),
    "cissp": ("cissp",),
    "cka": ("cka", "certified kubernetes administrator"),
    "ckad": ("ckad", "certified kubernetes application developer"),
    "cks": ("cks", "certified kubernetes security specialist"),
    "pmp": ("pmp",),
    "comptia": ("comptia", "comp tia"),
    "itil": ("itil",),
}

TAXONOMY: dict[str, tuple[str, tuple[str, ...]]] = {
    **{canonical: ("hard_skill", aliases) for canonical, aliases in HARD_SKILL_ALIASES.items()},
    **{canonical: ("responsibility", aliases) for canonical, aliases in RESPONSIBILITY_ALIASES.items()},
    **{canonical: ("certification", aliases) for canonical, aliases in CERTIFICATION_ALIASES.items()},
}

ALIAS_TO_CANONICAL: dict[str, str] = {
    alias.casefold(): canonical
    for canonical, (_kind, aliases) in TAXONOMY.items()
    for alias in aliases
}


__all__ = [
    "ALIAS_TO_CANONICAL",
    "CERTIFICATION_ALIASES",
    "HARD_SKILL_ALIASES",
    "RESPONSIBILITY_ALIASES",
    "TAXONOMY",
]
