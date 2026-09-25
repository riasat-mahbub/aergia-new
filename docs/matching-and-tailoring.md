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

Protocol v9 keeps the full-dossier API and submission contract. The helper
fetches the complete context into memory but gates what the agent can read:

1. Freeze the application's job details, user instructions, profile, complete
   Library dossier, template choices, and rendering capabilities into a
   context snapshot. The helper initially writes only the whitelisted job
   object to `evidence/job.json`, with `company`, `role`, `job_url`,
   `description`, and `user_instructions` at the root.
2. Before seeing the dossier, write a complete fictional CV for the target
   role to `output/ideal-target.md` and atomically rename it into place. The
   helper exposes the full context, including the dossier, in
   `evidence/context.json` only after this file is complete. The ideal target
   is a temporary authoring aid and is never submitted.
3. Rebuild the candidate from the now-visible dossier. Translate useful ideas
   from the ideal target through direct evidence, plausible ordinary
   inference, transferable framing, or truthful forward-looking language.
   Keep fixed facts and claims of completed work accurate; use role intent or
   growth language when past evidence is limited.
4. Preview through the canonical renderer and scanner. Use the evaluation
   dimensions, requirement and keyword transitions, recommendations, and ATS
   findings to improve job fit, term visibility, and ATS compatibility before
   focusing on layout. The preview returns the server-normalized candidate,
   evaluation ID, and candidate hash.
5. Iterate within the five-preview limit, batching high-impact score-directed
   changes. Select the attempt with the strongest credible job-fit and keyword
   results and the best resolution of ATS findings, subject to factual
   accuracy and readable text. Submit that exact candidate with its context
   hash, evaluation ID, and candidate hash. The user reviews the saved draft
   and chooses whether to accept it.

### Scanner-directed optimization and page use

The tailoring evaluation exposes numeric candidate values for job fit and
keyword visibility, comparisons against earlier previews, requirement and
keyword transitions, and categorized findings. Its ATS dimension is reported
through finding counts; the scanner also returns ATS guidance rather than a
single numeric ATS score. Review those values and findings on each preview.
Prioritize high-impact requirements, employer terminology, and ATS parsing
findings. A low-evidence soft-skill or technology gap can still be represented
through a specific transferable example or truthful future-facing language
such as readiness to learn; a non-actionable gap blocks unsupported past
claims, not relevant role intent. Do not invent fixed qualifications, past
client delivery, or specific documentation work.

Make score-relevant content changes before page-fit adjustments. Use a
readable, parser-friendly layout, but do not force one page or remove useful
job language at the expense of job-fit, keyword visibility, or legibility. If
content overflows, tighten repetition and low-value material before removing
strong matching evidence. Inspect the rendered PDF for ATS text recovery,
headings, breaks, crowding, and readable type. Do not use arbitrary CSS or
repeat terms without useful context.

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
identities/URLs, exact metrics, or security clearances. Keep claims about
completed work accurate while allowing plausible inference and transferable
framing for ordinary behavioral fit. Use scanner results to drive score
improvements, then review the credible, readable draft before deciding
whether to accept it.

Historical protocol-v8 drafts remain readable and can still be accepted or
rejected. New sessions use protocol v9 and the complete-dossier contract.
