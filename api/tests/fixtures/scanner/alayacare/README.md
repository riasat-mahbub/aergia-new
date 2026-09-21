# AlayaCare scanner regression fixture

`job_description.txt` is a plain-text copy of the posting supplied for the
scanner replacement. `cv_text_redacted.txt` is the extracted text of the
user-supplied one-page PDF, with the candidate name, email, phone number, and
external URLs redacted. The original PDF is not copied into the repository.

The source PDF is identified by the SHA-256 and byte count in
`annotations.json`. The redacted text derivative was extracted with
`pdfplumber` using `page.extract_text(layout=False)` and retains the job-related
content needed for these regression cases.

The source artifacts are frozen, but the labels are provisional agent
annotations and need user review before becoming gold data. This is a
development fixture, not a held-out evaluation set. The AI-assisted coding
label is intentionally partial: the CV says it built coding-agent and RAG
workflows, but does not say it used an AI tool to plan, generate, or test its
own code. These examples informed scanner design and cannot estimate
generalization accuracy or justify production cutover.
