# Evidence-driven application CV selection

## Decision

Profile is mandatory. Populated education is a baseline CV section and should
be retained whenever possible. There is no fixed hierarchy among experience,
skills, certifications, languages, projects, and research.

Those sections are selected by the value of their evidence for the specific
job. A row's value is based on new weighted requirement coverage, directness of
the match, complementary proof, and content quality. Stable Library order is
used only for exact ties.

Examples:

- A required CCNA certification makes matching certification content highly
  valuable and can outrank unrelated experience or projects.
- A React requirement can select both direct skills and projects that
  demonstrate React usage when each adds distinct evidence.
- Research publications and research experience become high-value when the job
  explicitly asks for research, publications, laboratories, or academic work.
- Education remains visible even when the job description assumes a degree.

## Fit behavior

The one-page fitter removes the candidate with the smallest current relevance
loss, rather than removing sections in a fixed order. Profile is never removed;
education is trimmed only after optional content and retains one entry when
possible. Rows that uniquely support a required requirement are protected.

## Data cleanup

Disposable application data is cleaned from the explicit local databases after
backups. Applications, status history, linked generated CVs, and orphaned CVs
with `metadata.application_id` are removed. Unrelated CVs, users, templates,
and Library entries remain. The smoke database is skipped when it has no
application schema.

## Verification

Use deterministic regression fixtures for certification, skill-plus-project,
research, education, irrelevant-section, duplicate-evidence, and page-fit
cases. Run backend/frontend tests, build and codegen checks, the smoke gate,
and `tracker rebuild && tracker validate`.
