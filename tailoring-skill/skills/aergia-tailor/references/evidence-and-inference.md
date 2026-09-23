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

Prefer stronger evidence when choosing between competing claims about the same underlying fact. Evidence strength determines confidence, not editorial importance. A lower-level explicit detail may be generalized, compressed, or omitted when a broader entailed or defensibly inferred capability is more relevant to the target role.

## 2. Preserve claim scope

Inference may broaden terminology, but it must not silently broaden the underlying history.

Examples:

- substantial Next.js work can support React familiarity;
- substantial Django work can support Python familiarity;
- React/TypeScript plus documented unit testing can support plausible Jest or Vitest familiarity;
- documented frontend testing can support a proposed Playwright or Cypress tool claim when the surrounding evidence makes it plausible;
- CI/CD deployment work can support deployment-pipeline familiarity;
- substantial SQL-backed backend work can support relational-database experience;
- sustained professional software development within a software company and collaborative engineering team can support familiarity with standard team-development practices such as iterative delivery, code review, issue tracking, version-control workflows, and Agile-style development when the surrounding evidence is consistent with them;
- repeated feature development, testing, deployment, and collaboration across projects can support experience working within a software-delivery lifecycle;
- professional work delivering software for external organizations can support client-facing or client-project experience when the supplied context establishes that the projects served clients;
- documented collaboration with developers and designers on feature delivery can support cross-functional software-team experience;
- sustained testing, bug fixing, and validation work can support quality-assurance and software-quality practices even when the source does not use those exact labels.

These support bounded claims such as `worked in Agile development environments`, `experience with collaborative software delivery`, or `familiarity with quality-assurance practices` when the surrounding evidence supports them.

They do not support invented details such as exact durations, ownership scope, team size, metrics, proficiency levels, specific ceremonies, Scrum Master responsibilities, sprint ownership, formal methodology certifications, or specific accomplishments unless those details are independently evidenced.

## 3. Prefer the most useful defensible abstraction level

Explicit evidence does not need to remain at its original level of specificity.

When a source detail is true but incidental to the target role, identify the broader capability that the detail demonstrates and decide which level of abstraction is most useful for the application.

Examples:

- Moodle or WordPress plugin work may be presented as web application, plugin, integration, API, support, or client-software experience when those descriptions accurately capture the work;
- work in a particular research domain may be presented through the software engineering, analysis, collaboration, or tooling capabilities it demonstrates when the domain itself is not relevant;
- a specific internal tool may be omitted when its underlying engineering responsibility is more valuable than the product name;
- a platform-specific implementation detail may be compressed into the broader development, testing, deployment, documentation, or support capability it demonstrates when the platform itself does not help the target application.

Preserve implementation-specific names when they are target-relevant, materially strengthen credibility, distinguish the candidate, or are necessary to understand the accomplishment.

Do not preserve a low-value concrete detail merely because it is explicit evidence while omitting a more useful entailed or strongly inferred capability.

Specificity is a presentation choice. Use the most specific defensible wording that improves relevance and credibility; otherwise prefer the broader supported capability.

## 4. Distinguish tool familiarity from detailed historical claims

An inferred ecosystem tool may be acceptable in a user-reviewed draft when the surrounding evidence makes it plausible.

For example:

- **Potentially acceptable:** `Jest familiarity`
- **Not justified by that inference alone:** `Designed a 400-test Jest platform that reduced regressions by 37%`

The first is a bounded inference. The second invents scope, activity, and an outcome.

The same rule applies to inferred professional practices.

For example:

- **Potentially acceptable:** `Worked in Agile-style development environments`
- **Not justified by context alone:** `Led Scrum ceremonies and owned sprint planning for a five-person team`

## 5. Treat high-risk factual claims conservatively

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

## 6. Absence is not always disproof

A source not naming a technology, practice, or standard professional behavior does not automatically mean the candidate lacks it.

Do not treat `not mentioned` as equivalent to `false`.

Instead ask:

- Is there surrounding evidence that makes the claim entailed or plausible?
- Does the candidate's sustained professional context make the practice ordinary and strongly implied?
- Is the proposed claim narrow enough to match that evidence?
- Would the user reasonably be able to verify or remove it during review?

A deterministic scanner or structured matcher reporting that something is not evidenced means only that it did not establish the claim from the material it evaluated. It is not, by itself, a prohibition on reasonable inference.

## 7. Explicit user corrections override inference

User corrections, exclusions, and prohibitions are authoritative.

Examples:

- `Do not claim AWS.`
- `I used Vitest, not Jest.`
- `Do not infer management experience.`
- `Do not split this project.`

Do not reintroduce a rejected claim later unless the user explicitly changes the instruction or new authoritative evidence resolves the conflict.

## 8. Resolve conflicting evidence carefully

When supplied sources disagree:

1. prefer explicit user-confirmed facts;
2. consider whether one source clearly represents a newer state of the same evolving fact;
3. consider source authority and specificity;
4. use the strongest mutually supported claim when uncertainty remains;
5. surface a material unresolved conflict for review.

Do not assume that a newer file timestamp means every fact in that file is newer.

## 9. Reframe and decompose without manufacturing experience

Evidence may be reorganized to expose a more relevant angle.

It is acceptable to:

- split a large project into meaningful facets;
- highlight a subsystem separately;
- reframe the same work around frontend, backend, ML, research, reliability, performance, tooling, delivery, quality, support, collaboration, or another genuinely supported angle;
- merge redundant source bullets;
- synthesize several source details into one stronger claim;
- generalize incidental implementation details into the broader capability they demonstrate when that better serves the target role.

Preserve provenance and attribution.

Do not:

- make one body of work appear to be several unrelated projects;
- duplicate the same accomplishment to inflate experience;
- imply separate employment or research engagements that did not exist;
- turn a subsystem into an independent product when it was not one;
- use abstraction to imply responsibilities or scope that the source evidence does not support.

## 10. Separate inference from final factual certainty

When a materially uncertain inference is useful, identify it for review rather than silently treating it as established fact.

Use the workflow's normal review-note or inference-note mechanism when available.

A useful review note should explain both the claim and its basis, for example:

> Jest inferred from documented React/TypeScript and unit-testing experience; verify before accepting.

Or:

> Agile development familiarity inferred from sustained professional feature delivery, testing, deployment, and collaboration within a software team; verify if needed.

Do not create review noise for trivial entailments or ordinary professional implications unless they are likely to matter to the user.

## 11. Do not infer merely to improve a score

Inference should improve the accuracy, relevance, or usefulness of the application material.

Do not add a technology, qualification, practice, or responsibility solely because:

- it appears in a job description;
- a keyword score is low;
- a matcher reports a gap;
- an ATS-oriented check would prefer the term.

A genuine qualification gap may remain a gap.

## 12. Prefer defensible alignment over literal source matching

The final wording does not need to reuse the source's exact vocabulary or preserve its original level of specificity.

You may:

- use an industry-standard term for an equivalent demonstrated practice;
- express an implication more directly;
- choose terminology that better matches the target role;
- combine several supported facts into a concise role-relevant statement;
- describe sustained collaborative professional software work using standard industry terminology when the surrounding evidence supports it;
- surface ordinary software-development practices that are strongly implied by the candidate's documented role and activities;
- generalize incidental platform-specific work into the underlying engineering capability when that better serves the target role.

The constraint is the underlying meaning, not the original sentence.

Do not preserve source specificity for its own sake. A concrete fact is valuable when it makes the candidate more credible, differentiated, or relevant—not merely because it is concrete.

## 13. User review permits useful but bounded inference

When the output is explicitly a draft that the user will review before use, reasonable inference can be more permissive than in an irreversible or fully automated workflow.

That does not remove truthfulness requirements.

Use this freedom to surface plausible experience the source may understate, while keeping uncertain claims narrow, reviewable, and easy to remove.

Prefer a narrow, defensible professional inference over an irrelevant explicit detail when the inference materially improves target relevance. This does not mean inventing history; it means selecting the most useful supported interpretation of the candidate's actual work.

## Final review test

Before keeping an inferred or reframed claim, ask:

- What evidence supports it?
- Is the relationship explicit, entailed, strong, reasonable, or merely speculative?
- Have I preserved the scope of the underlying evidence?
- Am I adding a tool/familiarity claim, or accidentally inventing detailed history?
- Am I inferring an ordinary professional practice from a context that genuinely supports it, or merely assuming it because it is common?
- Does any user correction contradict it?
- Would I be comfortable showing the user exactly why this inference was made?
- Am I preserving a low-value explicit detail merely because it is explicit, while omitting a more relevant capability that the evidence strongly supports?
- Is the level of specificity appropriate for the target, or would a broader but still defensible description communicate the candidate's value better?
- If the claim were removed, would the application become less accurate or merely score lower?

If the answer reveals weak support, inflated scope, score-chasing, or unnecessary low-value specificity, narrow, generalize, or remove the claim.
