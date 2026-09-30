# CV writing, searchability, and presentation

Optional reference for decisions about CV structure, readability, formatting,
and export. Consult it when useful; apply recommendations selectively to the
candidate and session. These suggestions are contextual, not universal ATS
requirements. The user's preferences and employer's application instructions
take precedence. Accuracy and the main skill's safety constraints remain
mandatory.

## Contact details and searchable structure

- Preserve supplied contact details and relevant professional links. City and
  region usually provide enough location detail; do not add a street address
  just to satisfy a checklist. Aergia restores server-owned profile identity
  fields during preview. Mention material missing information in review notes
  rather than inventing it or editing source records.
- Use recognizable, visible section headings that match the content, such as
  Work Experience, Education, Skills, and Projects. Use Personal Projects or
  Academic Projects only when that distinction is supported by the source. An
  early-career CV can emphasize education and projects without inventing
  employment to populate a heading.
- Include the target job title naturally in the summary when it describes the
  candidate's qualifications or explicit role intent. For example, "Seeking a
  Junior Software Developer role, applying…" does not claim the candidate has
  held that position. Preserve historical job titles. An exact title match is
  not a guarantee of recruiter discovery or ranking.
- Keep dates consistent and visibly associated with the correct role or degree.
  Prefer clear month/year formatting when the source contains that precision;
  do not invent months for year-only evidence.
- Match education advice to the actual job requirements. Finding an Education
  heading does not establish that a required qualification is satisfied.

## Recruiter-facing content

- Make the summary a brief, specific explanation of fit for this job, normally
  one or two sentences. Use relevant experience and projects to support it.
- Judge seniority using responsibilities, scope, and ownership as well as any
  explicit experience requirement. Do not invent a years-of-experience cutoff
  when the job does not give one.
- Prefer concrete contributions and outcomes. Use supported measurements with
  their units and attribution intact; qualitative outcomes are useful too.
  Do not chase a quota such as five metrics or manufacture numbers.
- Use employer terminology in meaningful context and follow the natural writing
  guide for tone. Keep transferable ability and future intent distinct from
  claims about completed work.
- Include relevant supplied portfolio, website, or professional-profile links
  with readable labels. For LinkedIn and GitHub profiles, prefer the direct
  address in visible text (`linkedin.com/in/handle` or `github.com/handle`)
  unless the user specified a custom label. For project and other links, show
  the domain and identifying path instead of a generic label. Keep project
  names, supplied dates, and links ahead of descriptions. Preserve
  explicit user labels and preferences, and keep link targets at the actual
  supplied destination, including meaningful path and query information. Use
  a shortened address only when the user supplies it as an existing URL; never
  invent one or make a long URL appear to resolve at a different address. Do
  not claim to have verified link contents unless read.
- Keep voice and formatting consistent across summary and description fields.
  When most comparable entries use bullets or lists, keep that format; when
  most use paragraphs, keep paragraphs. Use bullets for distinct points and a
  concise paragraph for one point when it suits the dominant format. When
  space is tight, convert related bullets into readable paragraphs across
  comparable entries before cutting useful content.
- Treat word count as a density signal, not a pass/fail target. Aim for one
  readable page while preserving strong job-fit evidence; retain two when a
  one-page version would materially weaken the application or crowd the text.

## Typography and layout using Aergia

- Choose a simple suitable template; Minimal is a reasonable starting point.
  Use only the session's supported styles and tokens.
- Keep heading and body fonts consistent across sections, normally using one
  or two families for the whole CV. Inspect section overrides as well as
  inherited defaults. Apply consistent choices in the candidate yourself;
  this does not require the user to adjust each section manually.
- Named fonts in generic advice, such as Open Sans, Roboto, and Lato, are
  examples rather than requirements. Do not invent font tokens or assume a
  named font is installed. Use available readable families.
- Use selective bold for the name, job titles, and company names through
  supported field styles and rich-text runs. Avoid making entire paragraphs
  bold or giving every element equal emphasis.
- Check contrast and readable size for all text, including dates and links.
  An acceptable average size can hide tiny individual fields. Avoid `xs` for
  sustained reading; try paragraph flow and supported spacing before removing
  useful content or shrinking text.
- Prefer left alignment for prose. Profile alignment is supported through
  `style.subsection.text_align`; inspect the rendered result because this is
  section-wide, not an independent summary-only control. Centered identity
  and contact details can remain when clear. Avoid justification by default.
- Keep entries consistent and reading order clear. Avoid putting essential
  information in images or layouts that interleave unrelated text. Decorative
  icons are not automatically a parsing failure; use PDF and scanner evidence.
- Keep essential contact information in document content. A profile block at
  the top of the first page is not the same as a repeating PDF header/footer.

## Margins, paper, and export

- Aim for comfortable page-edge whitespace. Margins of 0.5–1 inch are a useful
  starting preference when configurable, not a universal ATS threshold.
- Consult capabilities before changing margins or paper size. Section spacing
  does not set page margins. If page setup is template-owned, keep supported
  settings and note any material unmet employer requirement; do not invent
  fields, insert spaces to simulate margins, or claim unavailable adjustments.
- Use A4 or Letter as appropriate when supported. Inspect actual page breaks,
  clipping, and whitespace in the PDF rather than inferring them from settings.
- Use a concise, descriptive CV title so the exported filename is readable.
  Aergia exports PDF; do not claim another format was produced. Follow explicit
  employer format requirements where possible and disclose an incompatibility.
  Do not describe PDF as universally preferred by every ATS.
- Preserve meaningful punctuation, accents, and skill names such as C++.
  Repair observed missing or corrupt glyphs instead of stripping all special
  characters because a generic checklist warns about them.

## Applying these guidelines during previews

Use the actual PDF and scanner findings to assess contact visibility, headings,
date association, reading order, text size, clipping, and page breaks. Presence
in candidate JSON alone does not prove visibility or successful PDF extraction.
Distinguish observed problems from suggestions; a local scanner result does not
certify compatibility with every ATS.

When these recommendations are relevant, batch supported changes within the
main skill's five-preview budget and keep its priority order: meaningful
job-fit and keyword improvements, then ATS and one-page layout repairs. These
guidelines add no separate score, checklist artifact, validator, or submission
requirement. Report only checks actually performed.
