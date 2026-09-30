# Matching and tailoring

## Job Fit boundary

Application Job Fit evaluates the target job against the CV currently linked
to that application. It does not treat every item in the user's Library as
already visible in that CV. Tailoring gives the author the frozen profile,
Library history, and (when present) a clearly labeled readable source CV so
useful evidence can be included in a proposed draft. A source scan describes
the source CV; it is separate from the scan of a tailoring preview.

Tailoring previews scan temporary candidate documents and do not replace the
application's linked-CV scan. A submitted candidate remains an unlinked draft
until the user reviews and accepts it. Linking an accepted draft lets the
normal application lifecycle evaluate the linked CV.

## Scanner interpretation

At session creation, Aergia freezes a versioned requirement interpretation
for the target job. The same interpretation is used across previews so
changes reflect the candidate document rather than a changed job extraction.
Each preview evaluates the current canonical candidate and rendered PDF for
semantic requirement coverage, lexical visibility, presentation quality, PDF
recovery, and ATS guidance. The report describes the current CV's evidence and
visibility. An absent match is a gap in that CV; it does not establish that
the person lacks the ability or experience.

Job Fit and keyword dimensions expose numeric candidate values and meaningful
comparisons. ATS is represented by findings and guidance, not one numeric
score. Review required and preferred criteria, employer terminology,
recommendations, keyword transitions, parsing errors, reading order, and
warnings together. Treat these results as evidence about the current draft,
not as an automatic decision about the candidate.

## Skill identity

`api/app/scanner/skills.py` owns canonical identity for known technology
names used in scanning. Common aliases such as Postgres/PostgreSQL,
k8s/Kubernetes, JS/JavaScript, and React.js/React identify the same skill.
Aliases do not imply broader relationships such as cloud/provider or
container/tool equivalence. Unknown technology labels retain their normalized
identity; behavioral and umbrella relationships are evaluated semantically.

Structured constraints such as experience duration, degrees, certifications,
languages, authorization, and reliable location requirements remain distinct
from a technology-name match. A skill name appearing in a CV does not by
itself establish every related qualification or level of proficiency.

## Canonical rendering and scanning

React is the editing surface. The document renderer follows one path:

```text
Pydantic document AST → pure resolver → resolved render model
→ Python HTML renderer → Chromium PDF
```

The tailoring server validates and normalizes a complete candidate before
rendering and scanning it. Each preview returns that canonical candidate,
evaluation and scanner findings, and the exact PDF bytes. The server owns
mechanical and scanner-derived facts; the agent edits the candidate using
those results and inspects the rendered PDF for actual readability and text
recovery.

## Tailoring flow

New helper sessions use protocol v10. The browser URL remains
`/agent/tailor/$sessionId`; the helper is a portable skill that uses the
session link and one-time code. The helper keeps the scoped capability in
memory and does not use a normal Aergia access token.

1. The helper freezes the job, user instructions, profile, Library history,
   source CV when available, templates, document capabilities, and scanner
   context for the session. Before the blind stage is complete, the agent can
   read only `evidence/job.json` with `company`, `role`, `job_url`,
   `description`, and `user_instructions` at its root.
2. The agent writes a complete fictional, job-specific CV to
   `output/ideal-target.md` without candidate evidence, then atomically
   renames it into place. This is a temporary planning aid and is never
   submitted. The helper exposes `evidence/context.json` only after the file
   is complete.
3. The agent reads the full dossier, including the source CV when present,
   and writes a complete candidate. It may use direct evidence, reasonable
   professional inference, transferable framing, and truthful future intent.
   It keeps fixed facts and completed-work claims accurate and preserves
   employer, title, and date associations when ordering material by relevance.
4. The server validates and normalizes the candidate, reserves a preview,
   renders through the canonical document pipeline, and scans that exact
   preview. The helper stores the returned canonical candidate and PDF for
   that attempt.
5. The agent makes meaningful, high-impact edits within a limit of five
   successful previews. It selects the strongest credible version explicitly
   by `evaluation_id` and `candidate_hash`; there is no automatic preview
   ranking. The user chooses whether to accept the submitted draft.

The frozen context is a snapshot, not a live refresh. Changes to the target
job or user instructions, application ownership, linked source-CV identity or
revision, or compatible renderer/scanner contract can make it stale. Unrelated
profile, Library, or template edits do not silently replace its contents.

### Content, layout, and preview budget

Make relevant requirements and employer terms visible in the right context.
Ordinary professional inference and transferable framing can support a
behavioral expectation without a separate anecdote for every phrase. A
scanner gap does not bar a truthful statement of transferable ability or role
intent. Do not turn future intent into a past-tense achievement or invent
fixed facts, credentials, metrics, or completed work.

Keep the profile a short job-specific pitch and descriptions in a consistent
narrative format across comparable entries. Prefer paragraphs across
comparable entries when that format suits the source and helps fit the
strongest evidence on one readable page. Follow the user's preferences;
retain two pages when one page would remove material evidence or make the CV
crowded. Fix score-relevant content first, then consequential ATS parsing and
layout findings. Do not use arbitrary CSS or repeat terms without useful
context. Use a preview only when a meaningful improvement remains; the second
preview is not mandatory.

### Advisory independent PDF review

After choosing a likely attempt, the helper exports the exact stored PDF as
`candidate.pdf`, a `job.json` containing only `company`, `role`, and
`description`, and a manifest binding the package to `evaluation_id`,
`candidate_hash`, and `pdf_sha256`. A fresh host-delegated reviewer uses a
separate conversation and directory and receives only that package and the
review instructions in
`tailoring-skill/skills/aergia-tailor/references/independent-review.md`.
The package omits the dossier, ideal target, author history, application
notes, scanner scores, source identifiers, and capabilities. This workflow
separation is not an OS sandbox when the agent host shares filesystem access.
Aergia does not select or call a hosted model provider for the review; the
installed agent host supplies the delegated reviewer.

The author checks suggestions against the dossier and may make one
consequential revision followed by at most one review follow-up. The
`fit-review-v1` report is bound to the selected PDF. If the host cannot
delegate a reviewer or the reviewer cannot inspect PDFs, record `unavailable`
with a reason. Record `skipped_explicitly` only when the user explicitly asks
to skip. Do not label the author's own assessment as independent. Completed,
generic, unavailable, and explicitly skipped reports are advisory and never
block submission or acceptance; an absent report remains “Not run.”

### Owner review after submission

Submission creates an unlinked pending draft. Owner status for v10 includes
the current draft revision, canonical candidate hash, current evaluation and
PDF digest when available, and the fit review's applicability to that draft.
If the owner edits the CV, the prior evaluation may need reevaluation and a
previous fit review can describe an earlier version. Acceptance checks the
current CV revision and candidate hash; the advisory fit-review verdict does
not affect that check. Historical protocol 4–9 owner review remains readable.
