#!/usr/bin/env python3
"""Create presentation variants of the frozen Convverge job fixture."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / "benchmarks/job-requirements/corpus/real-jds-v1.jsonl"
OUTPUT = ROOT / "benchmarks/job-requirements/corpus/invariance/convverge-v1.jsonl"
CASE_ID = "convverge-junior-software-developer-v1"
SECTIONS = ("Key Responsibilities", "Qualifications and Experience", "Nice to Have")
FOLLOWING = {
    "Key Responsibilities": "Qualifications and Experience",
    "Qualifications and Experience": "Nice to Have",
    "Nice to Have": "Benefits",
}

SPLITS = {
    "Contribute to the design, development, testing, and support of client solutions in collaboration with senior developers and project teams.": [
        "Contribute to designing client solutions.",
        "Contribute to developing client solutions.",
        "Contribute to testing client solutions.",
        "Support client solutions.",
        "Collaborate with senior developers and project teams.",
    ],
    "Work within an Agile development environment, following team processes, coding standards, and delivery best practices.": [
        "Work within an Agile development environment.",
        "Follow team processes, coding standards, and delivery best practices.",
    ],
    "Break down problems into smaller tasks and seek guidance when needed to prioritize and move work forward.": [
        "Break down problems into smaller tasks.",
        "Seek guidance when needed to prioritize and move work forward.",
    ],
    "Support testing and quality assurance activities by reviewing functionality, documenting issues, and helping validate fixes.": [
        "Support testing and quality assurance activities.",
        "Review functionality.",
        "Document issues.",
        "Help validate fixes.",
    ],
    "Develop software components and solutions using Microsoft technologies, including the Power Platform, with support from experienced team members.": [
        "Develop software components and solutions using Microsoft technologies, including the Power Platform.",
        "Work with support from experienced team members.",
    ],
    "Communicate questions, blockers, risks, or delays early so the team can support successful project delivery.": [
        "Communicate questions, blockers, risks, or delays early.",
        "This helps the team support successful project delivery.",
    ],
    "Post-secondary education in Computer Science, Software Development, Information Technology, or a related program, or equivalent practical experience.": [
        "Post-secondary education in Computer Science, Software Development, Information Technology, or a related program.",
        "Equivalent practical experience is also accepted.",
    ],
    "Approximately 0–2 years of software development experience, including internships, co-op placements, academic projects, personal projects, or professional experience.": [
        "Approximately 0–2 years of software development experience.",
        "This can include internships, co-op placements, academic projects, personal projects, or professional experience.",
    ],
    "Foundational experience with at least one programming language, such as C#, JavaScript, TypeScript, Python, or a similar language.": [
        "Foundational experience with at least one programming language.",
        "Examples include C#, JavaScript, TypeScript, Python, or a similar language.",
    ],
    "Interest in Microsoft cloud technologies, including Power Platform, Azure, Microsoft 365, SharePoint.": [
        "Interest in Microsoft cloud technologies.",
        "Examples include Power Platform, Azure, Microsoft 365, and SharePoint.",
    ],
    "Ability to work both independently and collaboratively within a team environment.": [
        "Ability to work independently.",
        "Ability to collaborate within a team environment.",
    ],
    "Clear verbal and written communication skills, with a willingness to ask questions and share progress openly.": [
        "Clear verbal and written communication skills.",
        "Willingness to ask questions and share progress openly.",
    ],
}

PARAPHRASES = {
    "Contribute to the design, development, testing, and support of client solutions in collaboration with senior developers and project teams.": "Help design, build, test, and support client software alongside senior developers and project teams.",
    "Work within an Agile development environment, following team processes, coding standards, and delivery best practices.": "Use Agile team workflows and follow the team's processes, code standards, and delivery practices.",
    "Break down problems into smaller tasks and seek guidance when needed to prioritize and move work forward.": "Divide problems into manageable tasks and ask for guidance when priorities or next steps are unclear.",
    "Create and maintain as-built documentation for client solutions.": "Write and keep current as-built records for client solutions.",
    "Build and update technical support documentation for internal teams and client solutions.": "Prepare and maintain technical support guides for internal teams and client work.",
    "Support testing and quality assurance activities by reviewing functionality, documenting issues, and helping validate fixes.": "Review software behavior, record issues, and help verify fixes as part of testing and QA.",
    "Develop software components and solutions using Microsoft technologies, including the Power Platform, with support from experienced team members.": "With experienced colleagues' support, build software components with Microsoft tools such as the Power Platform.",
    "Communicate questions, blockers, risks, or delays early so the team can support successful project delivery.": "Raise questions, risks, delays, and blockers promptly so the team can keep project work on track.",
    "Post-secondary education in Computer Science, Software Development, Information Technology, or a related program, or equivalent practical experience.": "Complete post-secondary study in Computer Science, Software Development, IT, or a related area, or have equivalent hands-on experience.",
    "Approximately 0–2 years of software development experience, including internships, co-op placements, academic projects, personal projects, or professional experience.": "Have about zero to two years of software-development experience, which may come from internships, co-op, school or personal projects, or paid work.",
    "Foundational experience with at least one programming language, such as C#, JavaScript, TypeScript, Python, or a similar language.": "Have basic experience with one or more programming languages, for example C#, JavaScript, TypeScript, Python, or a comparable language.",
    "Basic familiarity with version control tools such as Git.": "Know the basics of version control tools, for example Git.",
    "Interest in Microsoft cloud technologies, including Power Platform, Azure, Microsoft 365, SharePoint.": "Be interested in Microsoft's cloud tools, such as Power Platform, Azure, Microsoft 365, or SharePoint.",
    "Ability to work both independently and collaboratively within a team environment.": "Be able to work on your own and cooperate with a team.",
    "Clear verbal and written communication skills, with a willingness to ask questions and share progress openly.": "Communicate clearly in speech and writing, ask questions, and share progress with the team.",
    "Exposure to Agile development practices through work, school, or project experience.": "Have encountered Agile software practices in a job, school, or project setting.",
    "Experience with Microsoft Azure, Azure DevOps, Microsoft 365, SharePoint, or Power Platform.": "Have used one or more of Microsoft Azure, Azure DevOps, Microsoft 365, SharePoint, or Power Platform.",
    "Experience with C#, PowerShell, Bash, APIs, databases, or web development frameworks.": "Have worked with C#, PowerShell, Bash, APIs, databases, or web frameworks.",
    "Previous experience working on client-facing, consulting, or team-based software projects.": "Have prior software project experience with clients, consulting work, or a team.",
}


def _read_source() -> str:
    rows = [json.loads(line) for line in CORPUS.read_text(encoding="utf-8").splitlines()]
    return next(row["text"] for row in rows if row["case_id"] == CASE_ID)


def _section_items(lines: list[str], heading: str) -> tuple[int, int, list[str]]:
    start = lines.index(heading) + 1
    next_heading = FOLLOWING[heading]
    end = lines.index(next_heading, start)
    items = [line.strip() for line in lines[start:end] if line.startswith("    ") and line.strip()]
    if not items:
        raise ValueError(f"No indented source items under {heading}")
    return start, end, items


def _replace_sections(source: str, render) -> str:
    lines = source.splitlines()
    replacements = []
    for heading in SECTIONS:
        start, end, items = _section_items(lines, heading)
        body = render(heading, items)
        replacements.append((start, end, body))
    for start, end, body in reversed(replacements):
        lines[start:end] = body
    return "\n".join(lines)


def main() -> None:
    original = _read_source()
    variants: dict[str, str] = {"original_bullets": original}

    def reorder(_heading: str, items: list[str]) -> list[str]:
        return [f"    {item}" for item in reversed(items)]

    variants["reordered_bullets"] = _replace_sections(original, reorder)

    def merge_pairs(_heading: str, items: list[str]) -> list[str]:
        return ["    " + "; ".join(items[index:index + 2]) for index in range(0, len(items), 2)]

    variants["merged_bullets"] = _replace_sections(original, merge_pairs)

    def fine_split(_heading: str, items: list[str]) -> list[str]:
        return [f"    {piece}" for item in items for piece in SPLITS.get(item, [item])]

    variants["finely_split_bullets"] = _replace_sections(original, fine_split)

    def prose(_heading: str, items: list[str]) -> list[str]:
        return [" ".join(items)]

    variants["prose_paragraph"] = _replace_sections(original, prose)

    def paraphrase(_heading: str, items: list[str]) -> list[str]:
        return [f"    {PARAPHRASES.get(item, item)}" for item in items]

    variants["paraphrased_bullets"] = _replace_sections(original, paraphrase)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "".join(
            json.dumps(
                {
                    "case_id": CASE_ID,
                    "variant": variant,
                    "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    "text": text,
                },
                ensure_ascii=False,
            )
            + "\n"
            for variant, text in variants.items()
        ),
        encoding="utf-8",
    )
    print(f"wrote {len(variants)} variants to {OUTPUT}")


if __name__ == "__main__":
    main()
