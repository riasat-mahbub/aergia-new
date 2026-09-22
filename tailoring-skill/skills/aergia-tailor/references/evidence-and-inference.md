# Evidence and inference rules

Use these rules whenever candidate-facing material is created or rewritten from a body of evidence. They apply broadly to CVs, cover letters, application answers, project summaries, portfolio text, LinkedIn/profile content, and similar job-application material.

The goal is to produce the strongest defensible claim that the available evidence supports. Do not limit writing to literal source wording, but do not turn a plausible inference into invented history.

## 1. Use an evidence hierarchy

Reason from the strongest available basis first:

1. **Explicit evidence** — directly stated in supplied material or confirmed by the user.
2. **Entailed meaning** — follows directly or almost directly from explicit evidence.
3. **Strong ecosystem inference** — highly plausible from sustained work in a surrounding technology, toolchain, or professional context.
4. **Reasonable professional inference** — plausible enough to propose in a user-reviewed draft, but should be surfaced when materially uncertain.
5. **Speculation** — weakly supported. Normally omit unless the workflow explicitly allows a reviewable speculative proposal and the user can verify it before use.

Prefer stronger evidence over weaker inference when both are available.

## 2. Preserve claim scope

Inference may broaden terminology, but it must not silently broaden the underlying history.

Examples:

- substantial Next.js work can support React familiarity;
- substantial Django work can support Python familiarity;
- React/TypeScript plus documented unit testing can support plausible Jest or Vitest familiarity;
- documented frontend testing can support a proposed Playwright or Cypress tool claim when the surrounding evidence makes it plausible;
- CI/CD deployment work can support deployment-pipeline familiarity;
- substantial SQL-backed backend work can support relational-database experience.

These do not support invented details such as exact durations, ownership scope, team size, metrics, proficiency levels, or specific accomplishments unless those details are independently evidenced.

## 3. Distinguish tool familiarity from detailed historical claims

An inferred ecosystem tool may be acceptable in a user-reviewed draft when the surrounding evidence makes it plausible.

For example:

- **Potentially acceptable:** `Jest familiarity`
- **Not justified by that inference alone:** `Designed a 400-test Jest platform that reduced regressions by 37%`

The first is a bounded inference. The second invents scope, activity, and an outcome.

## 4. Treat high-risk factual claims conservatively

Do not infer or invent:

- employers;
- employment dates;
- degrees or institutions;
- certifications or licenses;
- awards;
- publications;
- official job titles that materially change the role;
- concrete metrics;
- exact proficiency levels;
- detailed accomplishments or results;
- specific project scope that is not evidenced;
- URLs or identities.

These facts should come from explicit evidence or direct user confirmation.

## 5. Absence is not always disproof

A source not naming a technology or practice does not automatically mean the candidate lacks it.

Do not treat `not mentioned` as equivalent to `false`.

Instead ask:

- Is there surrounding evidence that makes the claim entailed or plausible?
- Is the proposed claim narrow enough to match that evidence?
- Would the user reasonably be able to verify or remove it during review?

A deterministic scanner or structured matcher reporting that something is not evidenced means only that it did not establish the claim from the material it evaluated. It is not, by itself, a prohibition on reasonable inference.

## 6. Explicit user corrections override inference

User corrections, exclusions, and prohibitions are authoritative.

Examples:

- `Do not claim AWS.`
- `I used Vitest, not Jest.`
- `Do not infer management experience.`
- `Do not split this project.`

Do not reintroduce a rejected claim later unless the user explicitly changes the instruction or new authoritative evidence resolves the conflict.

## 7. Resolve conflicting evidence carefully

When supplied sources disagree:

1. prefer explicit user-confirmed facts;
2. consider whether one source clearly represents a newer state of the same evolving fact;
3. consider source authority and specificity;
4. use the strongest mutually supported claim when uncertainty remains;
5. surface a material unresolved conflict for review.

Do not assume that a newer file timestamp means every fact in that file is newer.

## 8. Reframe and decompose without manufacturing experience

Evidence may be reorganized to expose a more relevant angle.

It is acceptable to:

- split a large project into meaningful facets;
- highlight a subsystem separately;
- reframe the same work around frontend, backend, ML, research, reliability, performance, tooling, or another genuinely supported angle;
- merge redundant source bullets;
- synthesize several source details into one stronger claim.

Preserve provenance and attribution.

Do not:

- make one body of work appear to be several unrelated projects;
- duplicate the same accomplishment to inflate experience;
- imply separate employment or research engagements that did not exist;
- turn a subsystem into an independent product when it was not one.

## 9. Separate inference from final factual certainty

When a materially uncertain inference is useful, identify it for review rather than silently treating it as established fact.

Use the workflow's normal review-note or inference-note mechanism when available.

A useful review note should explain both the claim and its basis, for example:

> Jest inferred from documented React/TypeScript and unit-testing experience; verify before accepting.

Do not create review noise for trivial entailments unless they are likely to matter to the user.

## 10. Do not infer merely to improve a score

Inference should improve the accuracy, relevance, or usefulness of the application material.

Do not add a technology, qualification, or responsibility solely because:

- it appears in a job description;
- a keyword score is low;
- a matcher reports a gap;
- an ATS-oriented check would prefer the term.

A genuine qualification gap may remain a gap.

## 11. Prefer defensible alignment over literal source matching

The final wording does not need to reuse the source's exact vocabulary.

You may:

- use an industry-standard term for an equivalent demonstrated practice;
- express an implication more directly;
- choose terminology that better matches the target role;
- combine several supported facts into a concise role-relevant statement.

The constraint is the underlying meaning, not the original sentence.

## 12. User review permits useful but bounded inference

When the output is explicitly a draft that the user will review before use, reasonable inference can be more permissive than in an irreversible or fully automated workflow.

That does not remove truthfulness requirements.

Use this freedom to surface plausible experience the source may understate, while keeping uncertain claims narrow, reviewable, and easy to remove.

## Final review test

Before keeping an inferred claim, ask:

- What evidence supports it?
- Is the relationship explicit, entailed, strong, reasonable, or merely speculative?
- Have I preserved the scope of the underlying evidence?
- Am I adding a tool/familiarity claim, or accidentally inventing detailed history?
- Does any user correction contradict it?
- Would I be comfortable showing the user exactly why this inference was made?
- If the claim were removed, would the application become less accurate or merely score lower?

If the answer reveals weak support, inflated scope, or score-chasing, narrow or remove the claim.
