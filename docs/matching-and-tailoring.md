# Matching and tailoring

## Job Fit boundary

Job Fit evaluates the application's currently linked CV against frozen job
requirements. The scanner never reads the Library or CandidateEvidence to
calculate that score. A qualification absent from the linked CV remains a scan
gap even when a Library source could supply it to a later tailored draft.

The matcher uses `api/app/scanner/skills.py` for technology identity. Known
spelling and product aliases collapse to a canonical ID, and unknown product
labels can match themselves with token boundaries. A skill appearing in Skills
or substantive CV prose is supported by identity; expectation strength does
not downgrade that presence. Structured constraints such as years, degrees,
certifications, authorization, and geography still have separate evidence
checks. Behavioral and contextual requirements remain in semantic rules.

## Vocabulary audit

| Previous owner | Classification and role after refactor |
|---|---|
| `scanner.skills.SKILL_ALIASES` | The one identity alias owner. It contains spelling and product-label identities, including Postgres/PostgreSQL, k8s/Kubernetes, JS/JavaScript, and React.js/React. |
| `relevance_taxonomy.HARD_SKILL_ALIASES` | Compatibility name pointing to `SKILL_ALIASES`; it no longer owns another mapping. Broader REST/RESTful, ASP.NET/.NET, and cloud/provider relationships were removed as identity aliases. |
| `relevance_taxonomy.TECHNICAL_CONCEPT_ALIASES` | Extraction concepts such as distributed systems and test automation. These keep independently meaningful terms in requirement parsing without defining product aliases. |
| `relevance_taxonomy.RESPONSIBILITY_ALIASES`; `scanner.matching._SEMANTIC_ALIASES` and `_SEMANTIC_PATTERNS` | Semantic relationship cues for behavior and context. Ordinary skill leaves bypass these rules. |
| `scanner.lexical._CUSTOM_TERMS` | Employer-term extraction cues that drive keyword visibility; not Job Fit identity. |
| `scanner.lexical._SURFACE_VARIANTS` | Display/wording variants for lexical visibility; they do not establish semantic or skill identity. |
| `candidate_evidence._normalized` | Provenance/excerpt validation and claim deduplication; not technology identity. |
| Frontend scanner report code | Display and explanation only; it performs no independent skill normalization. |

The legacy application-relevance service still has separate free-text/FTS
matching and builds a lowercase lookup table for its broader relevance
workflow. Its hard-skill alias source is the shared vocabulary, while the new
linked-CV scanner uses the shared boundary-aware extractor. Removing the
legacy service or its broader FTS behavior is outside this refactor.

## Tailoring stages

The staged tailoring protocol first interprets the job without candidate
material and extracts CandidateEvidence from one Library source at a time
without job context. The composition stage then receives the linked CV and
scan, an Opportunity Mapper result, CandidateEvidence, and a bounded selection
of original Library narratives. Opportunities are high-recall retrieval hints;
they do not modify Job Fit or assert that a claim is true.

Before rendering each staged draft, the local helper requires a hash-bound
claim-verification ledger for every enabled summary/description item. The
agent classifies each item as explicit, derived, inferred, or unsupported and
cites CandidateEvidence IDs or exact Library excerpts. Unsupported items cannot
render. Inferred items require a matching review note. Server evaluation also
blocks known technologies newly introduced without support in the linked CV,
Library, or user-confirmed facts. The server retains high-risk structured fact
checks and compares scan, ATS, quality, PDF, and pass results.

The local helper permits up to five evaluated passes. Its fallback choice
prioritizes safety, important regressions, ATS and resume quality, PDF recovery,
and concrete issue state before using Job Fit and term visibility as tie
breakers. The agent must inspect the PDF and perform editorial review on each
candidate; scores alone do not establish that a pass is acceptable.

## Limits

The claim ledger validates complete coverage, source references, and candidate
hashes mechanically. Whether a paraphrase is truly derived or a permitted
inference remains an editorial judgment by the tailoring agent and user. The
server's unsupported-skill check covers known technologies; unknown products
still require careful claim review. Opportunity retrieval uses deterministic
skill and word overlap, so semantic sources can be missed or retrieved even
when they ultimately do not support the wording.
