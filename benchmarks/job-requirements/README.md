# Job requirement extraction benchmark

This is a separate evaluation harness. It does not change Aergia's production
extractor.

## Status

The frozen source corpus contains 29 real postings. The first measured cohort
is not yet a complete bake-off: Small and Base have full-corpus runs, while the
current two-case oracle is preliminary and needs independent review. A broader,
independently reviewed oracle is still needed before treating aggregate
accuracy as a model selection result.

The purpose of keeping the larger corpus now is to freeze the input set and
make the checkpoint comparison reproducible. No candidate CV, Library, match,
or scanner result is part of this benchmark.

## Frozen corpus

`corpus/real-jds-v1.jsonl` contains 29 distinct descriptions: Convverge and
AlayaCare regression fixtures plus 27 real job descriptions already stored in
the local Aergia application database. Every description has a SHA-256 hash.
The database-derived descriptions are frozen in the JSONL so this run does not
depend on database state.

The current sample includes junior software, frontend, backend, full-stack,
ML/data, research, enterprise IT, client-facing, and cloud/DevOps roles. It
includes long postings so the production chunking path is exercised.

## GLiNER runs

Use the API virtual environment and make sure the pinned model snapshots are
available in the Hugging Face cache:

```bash
cd api
HF_HUB_OFFLINE=1 .venv/bin/python ../benchmarks/job-requirements/run_gliner.py --model small --local-files-only
HF_HUB_OFFLINE=1 .venv/bin/python ../benchmarks/job-requirements/run_gliner.py --model base --local-files-only
```

The runner loads the requested pinned checkpoint, then reuses Aergia's current
GLiNER runtime for chunking and the scanner's deterministic enrichment. For
Base, the only changed variable is the checkpoint. Both models use the same
`MODEL_LABELS`, a 384-word chunk, 64-word overlap, and the GLiNER2 library's
default extraction threshold (0.5); production does not pass a threshold
explicitly. The runner records both raw spans and the normalized scanner output.

Each run writes one JSONL record per job plus a metadata file under
`runs/gliner-{small,base}/`. The metadata records model revision, package
versions, device, load time, warm latency, and peak process RSS. Model weights
are not stored in this repository.

Create and run the six presentation forms with:

```bash
python benchmarks/job-requirements/build_invariance.py
HF_HUB_OFFLINE=1 api/.venv/bin/python benchmarks/job-requirements/run_invariance.py --model small --local-files-only
HF_HUB_OFFLINE=1 api/.venv/bin/python benchmarks/job-requirements/run_invariance.py --model base --local-files-only
```

## Oracle and scoring

`oracle/convverge-v1.json` is a source-verified, agent-reviewed seed from the
existing Convverge regression fixture. It covers candidate expectations,
responsibilities, qualifications, alternatives, and experience/education
constraints. It is explicitly marked preliminary: it has not had a second
human annotator adjudicate boundaries or semantics.

Score exact source-unit discovery and basic importance/type accuracy with:

```bash
python benchmarks/job-requirements/score.py \
  --oracle benchmarks/job-requirements/oracle/convverge-v1.json \
  --predictions benchmarks/job-requirements/runs/gliner-small/predictions.jsonl
```

The scorer reports raw candidate-requirement span coverage separately from
final Aergia source-unit discovery. A raw entity span counts as covering a gold
unit only when it overlaps at least half of the unit's non-whitespace
characters. Final source-unit discovery requires an exact normalized source
unit match. This avoids calling a model span such as “Junior Software
Developer” discovery of an entire requirement sentence.

## Other model status

The local host exposes no CUDA device, so the measured GLiNER runs are CPU runs.
NuExtract 1.5 Tiny was smoke-tested on Convverge with its Hugging Face
structured-output template format. The tested outputs were heading-only,
schema-incomplete, or repetitive; there is no full-corpus NuExtract run. NuNER Zero was not run: its
documented wrapper pins `gliner==0.1.12`, whose Flair dependency could not be
installed under this host's Python 3.14 because the required Gensim extension
does not build. PP-UIE was not run because Paddle's documented Python support
stops at 3.13 and this host has no Python 3.13 interpreter. These are setup
blockers, not model-quality results.

The official cards describe Base as a 194M parameter checkpoint, NuNER Zero as
an approximately 0.4B zero-shot NER model, and NuExtract Tiny as a 0.5B JSON
template extractor. See the [GLiNER2.5 Base card](https://huggingface.co/fastino/gliner2.5-base-v1),
[NuNER Zero card](https://huggingface.co/numind/NuNER_Zero),
[NuExtract Tiny card](https://huggingface.co/numind/NuExtract-1.5-tiny), and
[Paddle supported Python versions](https://www.paddlepaddle.org.cn/documentation/docs/en/install/index_en.html).

## Current pilot findings

See `runs/summary.md`. Small and Base each produced 22 final Convverge
requirements with the same source-unit boundaries. Base generated more raw
spans and took about twice as long on CPU, without increasing final discovery
coverage in the audited seed. The result is not enough to justify changing
production or selecting a winner: interpretation and the full human-audited
corpus remain open.
