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

The candidate index supports matching and scanner workflows. Protocol v9
tailoring does not use it to select or limit writer context: the tailoring
context contains one complete dossier made from the user's current profile and
every Library entry. This gives the agent the full source material for the
application in one place, including entries that do not appear relevant to an
initial keyword or semantic search.

## Tailoring flow

Protocol v9 follows this full-dossier flow:

1. Freeze the application's job details, user instructions, profile, complete
   Library dossier, template choices, and rendering capabilities into a
   context snapshot.
2. Read the dossier as a whole, select and shape the most relevant experience,
   projects, skills, and other material, then compose a complete target CV.
3. Preview the candidate through the canonical renderer and scanner. The
   preview returns the server-normalized candidate, evaluation ID, and
   candidate hash.
4. Submit that exact preview candidate with its context hash, evaluation ID,
   and candidate hash. The user reviews the saved draft and chooses whether to
   accept it.

Changes to the application, profile, or any Library entry make the frozen
context stale. Restart tailoring to load a fresh complete dossier; do not
continue from a partial refresh or submit against the old snapshot.

The preview candidate is canonical because the server normalizes document
content, including rich-text identifiers, before hashing and scanning. The
helper must keep the returned candidate unchanged through submission. Every
preview has its own evaluation ID, even when the candidate hash matches an
earlier preview. Submission binds to the selected preview through that ID and
hash; there is no separate editorial review payload or editorial approval
gate. The user still reviews the saved draft before accepting it.

Do not invent fixed high-risk facts such as employers, dates,
degrees/institutions, certifications, official titles, publications,
identities/URLs, exact metrics, or security clearances. A scan describes the
candidate against this job; it does not replace the user's judgment about the
draft.

Historical protocol-v8 drafts remain readable and can still be accepted or
rejected. New sessions use protocol v9 and the complete-dossier contract.
