# Matching and tailoring

## Job Fit boundary

Job Fit evaluates the application's target job against its currently linked
CV. The scanner never reads Library rows, CandidateEvidence, or cached
candidate semantics when scoring that CV. A Library skill absent from the
linked CV remains a Job Fit gap; tailoring can retrieve it as recoverable
candidate material.

Tailoring previews use temporary candidate scans. They do not replace the
application's stored scan. Accepting a draft links that CV and lets the normal
application scan lifecycle refresh Job Fit. Scanner results produced under an
older matching contract are stale by version and refresh through that same
lifecycle; historical applications are not eagerly rescanned.

## Skill identity

`api/app/scanner/skills.py` owns canonical skill identity for job extraction,
linked-CV scanning, deterministic Library indexing, and tailoring retrieval.
Known aliases collapse to one canonical ID, including Postgres/PostgreSQL,
k8s/Kubernetes, JS/JavaScript, and React.js/React. Aliases express identity;
they do not imply broader relationships such as cloud/provider or
container/tool equivalence.

Known skills use canonical lookup. Unknown job terms use safe whole-token
search against indexed CV and Library text, so a new product name does not
need to be pre-enumerated. Ordinary exact skill identity matches without a
separate proficiency or practical-use proof. Experience duration, degree,
certification, language, authorization, and reliable location constraints
remain separate structured checks. Collaboration and other behavioral
requirements remain semantic.

## Persistent candidate index

The deterministic index stores current source identity, fingerprints,
structured facts, canonical skills, and normalized searchable text. Library
mutations update the affected entry in the same database transaction. Legacy
rows receive persisted stable row IDs on their first index access. Narrative
source IDs combine the Library entry, row ID, and field path; fingerprints
hash the current extraction inputs.

Semantic propositions are stored per narrative source with the fingerprint,
model, extractor, prompt, and schema versions. Sources are `FRESH`, `STALE`, or
`MISSING`. A warm index causes zero candidate cue extraction, proposition
extraction, or indexing workers. A changed source invalidates only its own
semantic record. Before persisting a worker result, the backend locks and
rechecks the authoritative Library row and fingerprint. Deleted sources lose
both deterministic and semantic records.

At session start, one job-blind worker may receive a bounded batch of stale
sources. It receives no job, application, linked CV, scanner, or prior
conversation context. Each result is validated and persisted independently;
bad results remain stale without discarding valid peers. Refresh has a bounded
wait. Failure leaves stale semantic results unusable and tailoring continues
with the deterministic index and current original narratives.

The candidate index is a retrieval aid, not an authoritative whitelist of what
the writer may say. It never changes Job Fit. Retrieval is high-recall but
writer context is bounded by a character budget. Selected sources retain their
current original narrative, structured facts, stable source identity, and
fresh semantic record where available. A missing or stale semantic record does
not make an available original narrative unusable; the writer can interpret
and reframe it directly.

## Tailoring flow

Protocol v8 follows this relevance-first flow:

1. Check candidate semantic freshness and refresh only stale/missing sources.
2. Identify the job's highest-value priorities and what a recruiter should see
   immediately.
3. Retrieve Library material that supports or plausibly implies those
   priorities, then infer, abstract, combine, and reframe it aggressively.
4. Compose a complete target-specific CV, treating the linked CV as context
   rather than a fixed template.
5. Render and scan. Review the current CV's requirement, term, ATS, quality,
   PDF, and page-use diagnostics. Make another revision when it offers a
   material relevance improvement; otherwise select the strongest reviewed
   candidate and submit it for user review.

Ordinary professional inference appears directly in prose. Do not classify
every claim, require inference notes, or invoke another model because wording
is inferred. Do not invent fixed high-risk facts such as employers, dates,
degrees/institutions, certifications, official titles, publications,
identities/URLs, exact metrics, or security clearances. One strong draft and
one useful revision are latency guidance, not submission gates.

Each successful candidate preview has a unique evaluation ID, even when its
candidate hash matches an earlier preview. The editorial review and explicit
selection bind to both values. A finding does not decide whether a candidate
may be submitted; it remains visible in the user's saved draft review.

Optimize in this order: target relevance, requirement coverage, employer
terminology, strong reframing and inference, useful page-space allocation,
ATS/readability, and layout. `not_evidenced` means the current CV does not
establish a requirement yet; it does not prohibit writing toward it. Use the
scanner as an adversary for the current draft without mechanically maximizing
any single score.

## Limits

Submission binds the explicitly selected frozen candidate to the server's
`candidate_hash` and `evaluation_id`. The helper submits that candidate and the
server checks the normal candidate/evaluation/review binding. There is no local
claim ledger or inference-note gate. Unknown product names use deterministic
whole-token matching for retrieval; behavioral and ecosystem inference remain
part of the writer's relevance judgment and the user's final draft review.
