# Convverge Job Fit regression report

This report uses the complete posting in `job.json` and the unmodified
tailored CV in `candidate.json`. The previous column is the frozen scanner
result exported from the tailoring session; the new column is produced by the
current extraction → matching → aggregation → scoring path on 2026-09-22.

The canonical CV does not actually contain literal `collaboration`, `Agile`, or
`Azure` assertions, despite those signals being described in the investigation
brief. The report therefore records the result for the actual fixture rather
than adding synthetic evidence.

## Before / after requirement report

| Source requirement | Previous classification / status | New structured representation | CV evidence selected | Strength | New status | Reason for change |
|---|---|---|---|---|---|---|
| We are seeking a Junior Software Developer who is curious, motivated, and excited to grow in a collaborative technical environment. | Not extracted | candidate requirement; behavioral expectation leaf | None | — | Not shown | High-level candidate-facing sentence is retained; the CV does not state these traits directly. |
| You enjoy learning new technologies, solving problems, and turning business requirements into practical software solutions. | Not extracted | candidate expectation; learning/problem-solving leaf | None | — | Not shown | Candidate-facing prose is no longer silently discarded, but unsupported traits are not inferred. |
| You may be early in your career, but you bring strong fundamentals, a willingness to ask thoughtful questions, and a commitment to building reliable, high-quality work. | Opaque candidate block / Not shown | candidate expectation; ALL of `strong fundamentals`, `asking thoughtful questions`, `reliable high-quality work` | None | — | Not shown | Sentence is decomposed with source provenance; no CV evidence is fabricated. |
| Contribute to the design, development, testing, and support of client solutions in collaboration with senior developers and project teams. | Not extracted | job responsibility; collaboration responsibility | None in actual fixture | — | Not shown | The actual exported CV has no explicit collaboration sentence. |
| Work within an Agile development environment, following team processes, coding standards, and delivery best practices. | Not extracted | job responsibility; Agile/team-process leaf | None in actual fixture | — | Not shown | Agile is a genuine gap in the actual exported CV. |
| Break down problems into smaller tasks and seek guidance when needed to prioritize and move work forward. | Not extracted | job responsibility; task breakdown/guidance leaf | None | — | Not shown | Guidance language is preserved as a responsibility, not treated as generic experience. |
| Create and maintain as-built documentation for client solutions. | Documentation leaf / Not shown | documentation capability + as-built/client context | Research Assistant: documented empirical methods and findings; Associate Software Engineer documentation context | Partial transfer | Partial | Research documentation transfers to documentation, but not directly to client as-built records. |
| Build and update technical support documentation for internal teams and client solutions. | Documentation leaf / Not shown | documentation capability + technical-support/internal-client context | Research Assistant: documented empirical methods and findings; Associate Software Engineer documentation context | Partial transfer | Partial | Context is retained; technical documentation is useful evidence but does not prove support documentation. |
| Support testing and quality assurance activities by reviewing functionality, documenting issues, and helping validate fixes. | Not shown | testing/quality-assurance responsibility plus documentation subcomponent | Associate Software Engineer: unit and integration test suites; Delivery & Quality: Unit Testing/Integration Testing | Direct demonstration | Covered | Test work is matched as applied evidence, while documentation remains a related subcomponent. |
| Develop software components and solutions using Microsoft technologies, including the Power Platform, with support from experienced team members. | Not shown | practical-use responsibility; `Microsoft technologies` subject with illustrative Power Platform example | Summary: interested in Microsoft cloud and Power Platform solutions | Partial transfer | Partial | Interest is not promoted to demonstrated Microsoft implementation. `including` is not an AND checklist. |
| Communicate questions, blockers, risks, or delays early so the team can support successful project delivery. | Generic communication leaf / Not shown | proactive blocker communication responsibility | None | — | Not shown | Collaboration or written communication does not prove proactive escalation. |
| Post-secondary education in Computer Science, Software Development, Information Technology, or a related program, or equivalent practical experience. | Heading + flattened alternatives / Partial (`1 of 3`) | ANY(ANY of four education fields, equivalent practical experience) | Master of Computer Science; Bachelor of Computer Science and Engineering | Direct demonstration | Covered | Nested ANY semantics are evaluated recursively; Computer Science satisfies the outer requirement. |
| Approximately 0–2 years of software development experience, including internships, co-op placements, academic projects, personal projects, or professional experience. | Numeric children / Conflicting | one software-development-experience leaf + approximate duration constraint `{min: 0, max: 2}` + allowed evidence-source labels | Research Assistant and Associate Software Engineer dated entries; projects | Direct demonstration; constraint observation `above_approximate_range` | Covered | Bounds and evidence-source examples are no longer logical children; extra experience is surfaced separately from evidence absence. |
| Foundational experience with at least one programming language, such as C#, JavaScript, TypeScript, Python, or a similar language. | ANY language alternatives / Covered | explicit ANY alternatives; `such as` examples remain illustrative | C#/.NET work; Python project; Languages list | Direct demonstration | Covered | Alternative semantics remain explicit and multiple acceptable languages are evidenced. |
| Basic familiarity with version control tools such as Git. | Example list / Covered | Examples(subject: version control tools, Git illustrative) | Delivery & Quality: Git; Associate Software Engineer: Git and CI/CD | Strong related evidence / direct demonstration | Covered | Git familiarity is satisfied without counting the example as a second requirement. |
| Interest in Microsoft cloud technologies, including Power Platform, Azure, Microsoft 365, SharePoint. | Azure leaf / Not shown | interest expectation; Examples(subject: Microsoft cloud technologies, illustrative products) | Summary: interested in Microsoft cloud and Power Platform solutions | Direct demonstration | Covered | The umbrella interest is evaluated; `including` does not require every product. |
| Ability to work both independently and collaboratively within a team environment. | Opaque compound / Not shown | ALL(independent work, collaboration, team environment) | Aergia: end-to-end implementation and ownership-like project evidence | Partial transfer | Partial | Independent project evidence is retained; the actual fixture lacks direct team-collaboration wording. |
| Clear verbal and written communication skills, with a willingness to ask questions and share progress openly. | Not extracted | candidate expectation; communication, asking questions, open progress sharing | No direct blocker/progress assertion in actual fixture | — | Not shown | Written research documentation is not silently promoted to open progress sharing. |
| Exposure to Agile development practices through work, school, or project experience. | Not extracted | preferred exposure/familiarity expectation | None in actual fixture | — | Not shown | Preference is kept separate from required responsibilities. |
| Experience with Microsoft Azure, Azure DevOps, Microsoft 365, SharePoint, or Power Platform. | Azure-only leaf / Not shown | preferred prior experience; explicit ANY across five products | Summary: Microsoft cloud/Power Platform interest | Partial transfer | Partial | One OR branch and weaker interest evidence produce Partial; the result is not `1 of 5`. |
| Experience with C#, PowerShell, Bash, APIs, databases, or web development frameworks. | C# leaf / Covered | preferred prior experience; explicit ANY across six alternatives | C#/.NET work; Web & APIs skills; databases/project infrastructure | Direct demonstration / partial transfer | Covered | OR semantics allow a demonstrated C# branch to satisfy the preferred requirement. |
| Previous experience working on client-facing, consulting, or team-based software projects. | Not extracted | preferred prior experience; client-facing/consulting/team-based alternatives | No explicit client/consulting/team-based wording in actual fixture | — | Not shown | Project ownership is not automatically relabeled client-facing work. |

## Excluded source sentences

These are visible in the posting but do not enter the canonical candidate Job
Fit requirement set:

- `You'll work alongside developers, architects, and designers who take quality seriously, on projects that challenge you to think beyond the task in front of you.` — team/employer description.
- `We’re a close-knit, high-trust team that moves quickly, supports one another, and takes pride in delivering quality work.` — team description.
- `Our team shows up ready to do great work, and we expect the same from you. We collaborate, take ownership seriously, ask for help when needed, and hold each other to a high standard.` — mixed employer/team values statement.
- `In return, you’ll find a team that supports your growth and clients who genuinely value what we build together.` — employer value proposition.
- Benefits, company-value, hiring-process, and employer-platform prose are likewise excluded by section and sentence classification.

## Aggregate result

| Measure | Previous scanner | Current scanner |
|---|---:|---:|
| Visible source requirements | 15 | 22 |
| Covered | 3 | 7 |
| Partial | 1 | 5 |
| Not shown | 10 | 10 |
| Conflicting | 1 | 0 |
| Classified fraction | 0.80 | 1.00 |
| Job Fit | 0.2778 | 0.4985 |
| Qualification fit | no scored qualification bucket | 0.5833 |
| Responsibility alignment | 0.2333 | 0.2857 |
| Preferred fit | 0.5000 | 0.3750 |

The count increase is mostly the intentional promotion of candidate-facing
sentences and responsibilities that were previously omitted. The score is a
projection of the corrected evidence model, not an attempt to match Jobscan.
Repeated documentation requirements remain separately visible, while their
shared `documentation` concept group is normalized for aggregate weight.

## Jobscan comparison

| Requirement / concept | Our result | Jobscan observation | Source/CV evidence | Conclusion |
|---|---|---|---|---|
| Post-secondary education | Covered; nested ANY | JD does not specify education | Posting explicitly says post-secondary education; CV has Master and Bachelor of Computer Science | Jobscan is wrong on source parsing; the degree fully satisfies the alternative. |
| Software-development duration | Covered; approximate `0–2` constraint, with `above_approximate_range` observation | No specific years found | Posting explicitly says approximately `0–2 years`; CV has dated professional experience | Jobscan missed the numeric constraint; more evidence is not converted to Not shown. |
| Collaboration | Partial for the independent/collaborative compound | Collaboration signal detected | The actual exported fixture has end-to-end project evidence but no literal collaboration bullet; the investigation brief describes collaboration evidence | The scanner preserves the independent branch and does not invent collaboration in the canonical fixture. |
| Documentation | Partial for both context-specific responsibilities | Technical/support documentation signals detected | CV explicitly documents empirical methods and findings in research | Graded transfer is more faithful than either a full match or flat Not shown. |
| Microsoft cloud interest | Covered | Azure detected | CV summary explicitly states interest in Microsoft cloud and Power Platform solutions | Umbrella interest is covered; listed products are illustrative. |
| Preferred Microsoft experience | Partial | Azure detected | Posting is explicit OR; actual CV has interest evidence but no concrete Azure implementation bullet | Partial is due expectation/evidence strength, not `1 of 5`. |
| Programming / QA | Covered where supported | Programming and quality-assurance signals detected | CV has C#/.NET, multiple languages, unit/integration tests | The signals agree, but our result keeps source expectation and evidence context. |
| Consulting / client support | Not shown for the specific preferred context | Consulting and technical-support signals detected | CV has research and software work, not explicit client consulting/support documentation | Related vocabulary is not treated as unsupported full evidence. |

## Confirmed root causes

1. Indented posting bullets were not split reliably; heading/list extraction
   caused the education and duration bullets to be omitted or attached to a
   heading.
2. `_relation_tree` used flat connector grouping, and
   `_without_including_umbrella` deleted the subject of an `including` list.
   This lost nested ANY structure and confused illustrative lists with
   exhaustive requirements.
3. Numeric parsing attached duration bounds to leaves as if `0` and `2` were
   components. Constraint extraction and matching now have a distinct
   duration constraint and observations for unknown/within/above-range cases.
4. Employer/team classification was only partly section-based. Sentence-level
   employer/value-proposition classification now runs before candidate-section
   promotion.
5. Candidate-expectation prose had no decomposition path, so the whole sentence
   became an opaque fallback leaf.
6. Matching used exact concept/predicate support too aggressively. Directional
   aliases, semantic rules, expectation-specific transfer, and source-aware
   strength now distinguish direct, related, partial, weak, and unsupported
   evidence.
7. The scorer treated every source instance as full independent weight. Shared
   concept groups now normalize aggregate weight without merging source
   requirements or their contexts.
8. The drawer rendered every multi-leaf expression as an `N of M` checklist.
   ANY/Examples/compound alternatives now get relation-aware summaries, and
   semantic evidence strength is shown beside CV excerpts.

## Suspected issues that were not confirmed

- Jobscan’s education and years observations are source-parser misses, not
  evidence that Aergia should imitate keyword heuristics.
- The existing aggregate evaluator was not the first loss point for education;
  once the nested expression reaches it, it already evaluates ANY recursively.
- Summary and skills sections were not globally ignored. Their weakness was
  expectation/source-specific scoring, which is now explicit rather than a
  blanket trust or distrust rule.
- Repeated documentation was not destructively deduplicated. The issue was
  aggregate weighting, so source instances stay separate and only their shared
  concept weight is normalized.

## Remaining limitations

- The canonical CV artifact and the investigation brief disagree about literal
  collaboration, Agile, and Azure evidence. The regression deliberately uses
  the artifact and reports those gaps instead of adding synthetic text.
- Date-based experience totals currently use visible dated experience entries;
  project duration without structured dates remains duration-unknown.
- Semantic transfer is deterministic and reviewable, not a general-purpose
  ontology. New domains may need an explicit alias/rule and corresponding
  directional test.
