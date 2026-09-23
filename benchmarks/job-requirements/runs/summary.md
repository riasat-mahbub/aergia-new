# Model bake-off: first measured pass

## Scope and confidence

This is a benchmark pilot, not a production-model selection. It freezes 29
real job descriptions and contains a source-verified seed oracle for Convverge
and an existing provisional seed oracle for AlayaCare. Both oracle records are
agent-reviewed and explicitly require independent human review. They are not
an unbiased held-out set: AlayaCare labels were created for scanner work, and
the Convverge seed overlaps the existing regression fixture. Aggregate
accuracy claims across all 29 jobs are therefore not available yet.

The current machine has 20 CPU cores, 30 GiB total RAM, and no available CUDA
device. All measured runs below used CPU with `torch.float32`. The measured CPU
latency is not a 4-vCPU deployment measurement.

## Corpus

| Item | Value |
|---|---:|
| Frozen job descriptions | 29 |
| Long-document path | 26 |
| Short-document path | 3 |
| Corpus SHA-256 | `1bc04f650a3c680ea000fc99137c0d5fd579f7db53dfafa37fa5c89896e41820` |
| Audited seed oracles | Convverge: 22 units; AlayaCare: 16 units |

The seed oracle difficulty mix is 5 easy, 15 medium, and 18 hard source units.
It is useful for checking the mechanics and known difficult cases, but too
small and too closely tied to current fixtures to estimate general accuracy.

| Model | Approx. params | Source recall / precision | Hard source recall | Grounding | Warm CPU median | Peak RSS | Status |
|---|---:|---:|---:|---|---:|---:|---|
| GLiNER2.5 Small | 74M | 38/38, 38/38 on the two seeds | 18/18 | Exact source boundaries on both seed JDs | 0.92 s/job | 1.92 GiB | Measured, preliminary |
| GLiNER2.5 Base | 194M | 38/38, 38/38 on the two seeds | 18/18 | Exact source boundaries on both seed JDs | 2.14 s/job | 2.89 GiB | Measured, preliminary |
| NuExtract 1.5 Tiny | 500M | 0/22 valid Convverge requirements | 0/13 on Convverge hard units | Returned source headings, not requirements | 10.87 s/job | 3.49 GiB | One diagnostic case; failed |
| NuNER Zero | 400M | — | — | — | — | — | Not run: Python 3.14 dependency build blocker |
| PP-UIE 0.5B | 500M | — | — | — | — | — | Not run: no supported Python 3.13 runtime |

The 38/38 values above are provisional pilot scores, not an independently
annotated quality result.

## GLiNER checkpoint comparison

Both checkpoints used Aergia's exact `MODEL_LABELS`, the same 384-word chunks,
64-word overlap, flat overlap policy, confidence and offset return, and the
same `extract_requirements_from_entities` deterministic parser. The only model
change was the checkpoint. Neither call passes a threshold; the installed
GLiNER2 API default is 0.5.

| Model | Params | Jobs | Raw spans | Final requirements | Load | First inference | Warm median | Warm total | RSS after load | Peak RSS |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| GLiNER2.5 Small | 74M | 29 | 516 | 524 | 1.17 s | 0.96 s | 0.92 s | 25.87 s | 1.17 GiB | 1.92 GiB |
| GLiNER2.5 Base | 194M | 29 | 1,449 | 624 | 1.87 s | 2.08 s | 2.14 s | 62.59 s | 1.62 GiB | 2.89 GiB |

Base emits 2.8 times as many raw spans and 19% more final requirement objects
over the full corpus. That is not evidence that the extra objects are correct:
the complete corpus has not been independently annotated. On the two seed
cases, both produce exactly the same 22/22 Convverge and 16/16 AlayaCare source
units with no exact-boundary extras. Base does not improve discovery there.

### Seed-oracle details

| Model | Case | Exact source-unit recall / precision | Importance accuracy | Family accuracy |
|---|---|---:|---:|---:|
| Small | Convverge | 22/22, 22/22 | 19/22 (86.4%) | 21/22 (95.5%) |
| Base | Convverge | 22/22, 22/22 | 19/22 (86.4%) | 18/22 (81.8%) |
| Small | AlayaCare | 16/16, 16/16 | 12/16 (75.0%) | 13/16 (81.3%) |
| Base | AlayaCare | 16/16, 16/16 | 12/16 (75.0%) | 13/16 (81.3%) |

These are source-boundary and coarse-type checks, not semantic concept or
constraint accuracy. The oracle sources need independent review before these
figures should be treated as quality scores.

### Convverge semantic structure spot checks

These manual checks use the seeded requirement structure and inspect the
normalized Aergia output. Small and Base produced the same result for each
listed term set except for one duplicated duration constraint in Small:

| Requirement | Expected structure | Small | Base |
|---|---|---|---|
| Education | Computer Science / Software Development / IT / related program OR equivalent practical experience | Nested `ANY` retained; expected terms present | Same |
| Experience | Approximate 0–2 years plus five allowed source types | Bounds, approximate flag, and all five source types retained; duration attached twice | Same values and sources; attached once |
| Programming language | At least one language; C#, JavaScript, TypeScript, Python are examples | `ANY`; all four listed terms retained | Same |
| Preferred Microsoft products | `ANY` of Azure, Azure DevOps, Microsoft 365, SharePoint, Power Platform | 4/5; SharePoint missing | 4/5; SharePoint missing |
| Preferred tools | `ANY` of six listed tools/concepts | 6/6 | 6/6 |
| Client/consulting/team projects | `ANY` of client-facing, consulting, or team-based software projects | 2/3; consulting missing | 2/3; consulting missing |

This is a concrete interpretation limitation shared by both checkpoints.
The final source sentence is discovered, but the taxonomy/parser does not
preserve every branch in two alternative lists.

## Raw model spans versus deterministic enrichment

On Convverge, Small produced 1 raw `candidate_requirement` span and Base
produced 3. None covered at least half of any complete gold source unit. On
AlayaCare, Small produced 0 such spans and Base produced 8; again none covered
half of a full source unit. Other GLiNER labels overlap some candidate source
units (Small: 7/22 and 5/16; Base: 17/22 and 13/16), which can act as cues but
does not amount to full requirement discovery.

The Aergia result is different: deterministic section and sentence handling
returns all annotated source units for both seed fixtures with exact boundaries.
This means raw GLiNER sentence spans are not the main source of the apparent
discovery recall on these cases. The benchmark separates that behavior rather
than crediting the checkpoint alone.

## Convverge presentation invariance

The same Convverge facts were supplied as original bullets, reordered bullets,
paired/merged bullets, finely split clauses, prose, and a close paraphrase.
Small and Base produced the same final item counts for all forms:

| Form | Small final units | Base final units | Surface-text Jaccard vs original |
|---|---:|---:|---:|
| Original bullets | 22 | 22 | 1.000 |
| Reordered bullets | 22 | 22 | 1.000 |
| Merged pairs | 13 | 13 | 0.129 |
| Finely split clauses | 39 | 39 | 0.196 |
| Prose paragraph | 22 | 22 | 1.000 |
| Paraphrased bullets | 22 | 22 | 0.073 |

The surface-text Jaccard is an exact normalized-text comparison. Its low value
for paraphrase is expected and is not a semantic failure score. The count
changes for merged and split forms are material: merging two source bullets
into one sentence group reduces the scanner output by 41%; splitting clauses
increases it by 77%. Inspection shows the merged result joins two adjacent
requirements into one source object, while the split result promotes the
subclauses as separate objects. Both checkpoints behave the same. This points
to Aergia's sentence/source-unit segmentation as the source of this invariance
failure, not a checkpoint-capacity difference.

Reordering and moving the bullets to prose preserve all 22 exact source units.
The paraphrase produces 22 outputs but changes their text; no blinded semantic
review was performed, so only its count stability is established.

## NuExtract Tiny diagnostic

The pinned NuExtract 1.5 Tiny checkpoint was run on the complete Convverge
description using the model-card `<|input|>` JSON-template format, deterministic
decoding, and a 4,000-token generation cap. It returned parseable JSON with
three records, but those records were only section headings (`What We Offer`,
`About Our Team`, `About You`). Type and importance fields were blank. It matched
0 of the 22 seed requirements and omitted all 22. Loading used 1.13 seconds;
inference used 10.87 seconds; peak process RSS was 3.49 GiB on CPU.

This is a clear failure on the Convverge control, so a 29-job generation run
would not be a useful accuracy benchmark without first tuning its template.
That tuning would be a separate experiment and should be compared against the
same frozen prompt budget for all models.

## Models not run

NuNER Zero and PP-UIE have no quality result. NuNER's documented installation
uses `gliner==0.1.12`; the required Flair/Gensim setup failed to build under
Python 3.14.7. PP-UIE was skipped because the current official Paddle install
documentation supports Python only through 3.13, and this host has no Python
3.13. Neither model was silently treated as a failed predictor.

## Decision

**Keep GLiNER2.5 Small as the unchanged production baseline. Do not promote
Base or NuExtract based on this pilot.** Base costs about 2.3 times the warm
CPU latency and about 50% more peak RSS while showing no source-unit discovery
gain on the two seed cases. It changes some family labels for the worse on
Convverge. NuExtract's documented template produced no usable requirements on
the control.

This is a conservative decision, not proof that Small has the best accuracy.
The hard-case structure work is still split between deterministic enrichment
and model spans. Current evidence points to two separate issues: GLiNER does
not emit complete requirement sentences as raw candidate spans, and the
sentence-level deterministic segmentation changes object boundaries when
bullets are merged or split. More model capacity did not fix either issue.

The local outputs do not establish whether an LLM interpretation pass is
necessary for production. They do establish that a larger GLiNER checkpoint is
not a demonstrated fix. Before any production architecture change, independently
annotate a held-out set across the remaining 27 jobs, run NuNER/PP-UIE in a
supported environment, and evaluate structured constraint and AND/OR accuracy.
The measured memory suggests Small and Base can fit within 8 GiB on this host,
but 4-vCPU/8-GiB production feasibility and latency have not been tested.
