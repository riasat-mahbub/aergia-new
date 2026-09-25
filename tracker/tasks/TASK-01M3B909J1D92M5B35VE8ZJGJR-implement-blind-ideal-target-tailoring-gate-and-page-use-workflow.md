---
SCHEMA: 4
FORMAT: project-tracker
ID: TASK-01M3B909J1D92M5B35VE8ZJGJR
TYPE: task
STATUS: DONE
PRIORITY: null
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS:
- tailoring
RELATIONS:
  supersedes: []
AFFECTS:
  files:
  - tailoring-skill/skills/aergia-tailor/scripts/session.mjs
  - tailoring-skill/tests/session.test.mjs
  - tailoring-skill/skills/aergia-tailor/SKILL.md
  - tailoring-skill/skills/aergia-tailor/references/natural-writing.md
  - tailoring-skill/README.md
  - tailoring-skill/AGENTS.md
  - docs/matching-and-tailoring.md
LINKS: null
VERIFIED_BY: riasat1998
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-09-25T03:16:06.337284+00:00'
UPDATED_AT: '2026-09-25T03:16:06.337284+00:00'
---

# Implement blind ideal-target tailoring gate and page-use workflow

## Background

Implement the protocol v9 blind ideal-target stage, evidence-grounded candidate workflow, adversarial editing pass, and readable page-use policy across the session helper, skill instructions, and documentation.

## Investigation


## Decision


## Implementation

Added a blind authoring stage to the session helper. Stage zero writes only
the whitelisted job object (`company`, `role`, `job_url`, `description`, and
`user_instructions`) at the root of `evidence/job.json`. After the agent
atomically completes the fictional, job-specific `output/ideal-target.md`,
the helper exposes the full context through `evidence/context.json` and moves
from `awaiting_ideal_target` to `awaiting_candidate`.

Updated the skill instructions to rebuild the candidate from direct evidence,
reasonable inference, or adjacent experience; challenge both job fit and
factual support after preview; and prefer a readable one-page CV, filling
space with supported evidence before supported spacing and typography
changes. Documented the same flow and page policy. Kept the protocol v9 API,
preview binding, and submission behavior unchanged; the ideal target remains
a temporary authoring artifact and is not submitted.

Clarified that the profile is a concise job-specific fit pitch rather than a
recap of the full CV. The post-preview pass now checks
`evaluation.recommendations`, `evaluation.non_actionable_gaps`, and
`scanner_result.semantic.requirements` before layout edits or preview
selection. Updated the workflow to make the numeric job-fit and keyword
dimensions, score deltas, item-level requirements/keyword transitions, and
ATS findings the primary iteration signals. ATS is represented through
finding counts and guidance rather than one numeric score. The skill now
uses plausible ordinary inference, transferable examples, and truthful
forward-looking language for lower-evidence fit; a non-actionable gap blocks
unsupported past claims but does not require dropping the job theme. Fixed
facts and claims of completed work remain accurate. Content optimization
precedes page fit, and preview selection favors the strongest score results
subject to truth and readability. Synced the repository skill to the
installed copy.

A direct skill review found that the first-draft instructions referred to
matching suggestions that only arrive after preview. Clarified that timing,
gave the profile a concise job-pitch shape, and replaced the dense preview
paragraphs with an ordered score-and-findings loop. The writing reference now
allows important employer terms when they describe candidate work or credible
intent. The skill also points to the supplied capability schema for candidate
fields and calls for non-echoing code input.


## Verification

Focused helper tests passed. `tracker rebuild` completed and
`tracker validate` reported 0 errors with 7 existing fork warnings.

For the follow-up skill wording, `quick_validate.py` and `git diff --check`
passed; `cmp` confirmed the installed and repository skill files match. No
tests were run for that text-only correction. The final tracker rebuild
completed and validation reported 0 errors with 7 existing fork warnings.

For the score-optimization update, `quick_validate.py` and `git diff --check`
passed; `cmp` again confirmed the installed copy matches. No tests were run.
`tracker rebuild` indexed 624 entries; `tracker validate` reported 0 errors
with 7 existing fork warnings.


## Follow-up
