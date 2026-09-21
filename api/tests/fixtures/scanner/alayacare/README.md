# AlayaCare scanner regression fixture

`job_description.txt` is a plain-text copy of the posting supplied for the
scanner replacement. `cv_text_redacted.txt` is the extracted text of the
user-supplied one-page PDF, with the candidate name, email, phone number, and
external URLs redacted. The original PDF is not copied into the repository.

The source PDF is identified by the SHA-256 and byte count in
`annotations.json`. The redacted text derivative was extracted with
`pdfplumber` using `page.extract_text(layout=False)` and retains the job-related
content needed for these regression cases.

The source artifacts are frozen. `source_unit_annotations` labels every
sentence produced by the current segmenter; the requirement list includes the
two candidate-facing role-overview sentences as low-importance-context
responsibilities. Guidance, supervision, and “to learn best practices” are
recorded as employer context, not additional candidate qualifications.

The labels remain provisional and need user review before becoming gold data.
This is a development fixture, not a held-out evaluation set. AI-assisted
coding is partial: the CV describes coding-agent and RAG workflows, but does
not say that an AI tool was used to plan, generate, or test the candidate’s own
code. The lexical findings intentionally report GenAI, automated tests, and
containerization wording as absent while keeping their semantic support
separate. These examples informed scanner design and cannot estimate
generalization accuracy or justify production cutover.
