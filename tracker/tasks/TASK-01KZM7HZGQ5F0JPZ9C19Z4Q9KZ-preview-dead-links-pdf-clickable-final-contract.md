---
SCHEMA: 3
FORMAT: project-tracker
ID: TASK-01KZM7HZGQ5F0JPZ9C19Z4Q9KZ
TYPE: task
STATUS: DONE
PRIORITY: Medium
SEVERITY: null
EFFORT: S
OWNER: null
CONFIDENCE: Medium
TAGS: null
RELATIONS:
  supersedes:
  - TASK-01KZM4Z1TFRXWJT4HHP368Y21A
  - TASK-01KZM4MZ7F9QK8JVRGZ8EM4AXQ
AFFECTS: null
LINKS: null
CREATED_BY: null
UPDATED_BY: null
CREATED_AT: '2026-08-09T21:41:11.319439+00:00'
UPDATED_AT: '2026-08-09T21:41:11.319439+00:00'
---

# Preview dead links, PDF clickable — final contract

## Background

Supersedes TASK-01KZM4Z1TFRXWJT4HHP368Y21A and TASK-01KZM4MZ7F9QK8JVRGZ8EM4AXQ. Final direction per user: live preview must NOT have working links; exported PDF must. Preview endpoints (/render/html?preview=true, /cvs/{id}/preview) restore strip_anchor_hrefs (href->'#', markup+arrow preserved); iframe sandbox back to allow-scripts allow-same-origin. PDF paths keep raw renderer output -> real anchors -> clickable Chromium annotations (verified: /Subtype /Link + /URI in generated PDF, pdftotext shows 'Repo \u2197'). Root cause of the earlier reversal: the original request text was inverted vs intent; my clarifying ask re-confirmed only the PDF half.

## Investigation


## Decision


## Implementation


## Verification


## Follow-up
