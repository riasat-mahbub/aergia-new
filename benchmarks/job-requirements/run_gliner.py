#!/usr/bin/env python3
"""Run a pinned GLiNER2 checkpoint through Aergia's current scanner path."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import sys
import time
from pathlib import Path
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
sys.path.insert(0, str(ROOT / "api"))

from app.scanner.extraction import SCANNER_EXTRACTOR_VERSION, extract_requirements_from_entities  # noqa: E402
from app.services.requirement_extractor import (  # noqa: E402
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_GLINER2_MODEL,
    DEFAULT_GLINER2_REVISION,
    GlinerRuntime,
    MODEL_LABELS,
)

MODELS = {
    "small": (DEFAULT_GLINER2_MODEL, DEFAULT_GLINER2_REVISION),
    "base": ("fastino/gliner2.5-base-v1", "1a8bc24e00dc7300b9017c81d63e3dcdabb26596"),
}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def _load_model(model_name: str, revision: str, *, local_files_only: bool, device: str):
    from huggingface_hub import snapshot_download
    from gliner2 import AutoExtractor

    local_path = snapshot_download(
        repo_id=model_name,
        revision=revision,
        local_files_only=local_files_only,
    )
    return AutoExtractor.from_pretrained(local_path, map_location=device).eval()


def _peak_rss_gib() -> float:
    # Linux reports ru_maxrss in KiB.
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3)


def _current_rss_gib() -> float | None:
    status = Path("/proc/self/status")
    if not status.exists():
        return None
    for line in status.read_text().splitlines():
        if line.startswith("VmRSS:"):
            return round(int(line.split()[1]) / 1024 / 1024, 3)
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument(
        "--corpus",
        type=Path,
        default=ROOT / "benchmarks/job-requirements/corpus/real-jds-v1.jsonl",
    )
    parser.add_argument("--case-id", help="Run one corpus record; useful for a quick reproducibility check.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    import torch
    import transformers
    import gliner2

    model_name, revision = MODELS[args.model]
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is not available")

    records = _read_jsonl(args.corpus)
    if args.case_id:
        records = [record for record in records if record["case_id"] == args.case_id]
        if not records:
            raise SystemExit(f"No corpus record with case_id={args.case_id!r}")

    out_dir = ROOT / f"benchmarks/job-requirements/runs/gliner-{args.model}"
    prediction_path = out_dir / "predictions.jsonl"
    existing: dict[str, dict[str, Any]] = {}
    if prediction_path.exists():
        existing = {row["case_id"]: row for row in _read_jsonl(prediction_path)}
    if args.overwrite and args.case_id:
        existing.pop(args.case_id, None)
    elif args.overwrite:
        existing.clear()

    load_started = time.perf_counter()
    model = _load_model(model_name, revision, local_files_only=args.local_files_only, device=device)
    load_seconds = time.perf_counter() - load_started
    rss_after_load_gib = _current_rss_gib()

    # GlinerRuntime supplies the exact production long-document behavior. The
    # preloaded model is injected so this script can pin a non-production
    # checkpoint without changing production configuration.
    runtime = GlinerRuntime(
        model=model,
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )
    run_rows = list(existing.values())
    inference_times = []
    for index, record in enumerate(records, start=1):
        if record["case_id"] in existing and not args.overwrite:
            continue
        source = record["text"]
        started = time.perf_counter()
        spans = runtime.extract_entities(source, MODEL_LABELS)
        inference_seconds = time.perf_counter() - started
        inference_times.append(inference_seconds)
        extractor_version = f"{model_name}@{revision}+{SCANNER_EXTRACTOR_VERSION}"
        normalized = extract_requirements_from_entities(
            source,
            spans,
            extractor_version=extractor_version,
        )
        run_rows.append(
            {
                "case_id": record["case_id"],
                "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                "raw_spans": [
                    {
                        "label": span.label,
                        "text": span.text,
                        "start": span.start,
                        "end": span.end,
                        "confidence": span.confidence,
                    }
                    for span in spans
                ],
                "requirements": normalized.model_dump(mode="json"),
                "inference_path": runtime.last_inference_path,
                "inference_seconds": round(inference_seconds, 3),
            }
        )
        print(
            f"{index}/{len(records)} {record['case_id']} "
            f"spans={len(spans)} requirements={len(normalized.requirements)} "
            f"path={runtime.last_inference_path} seconds={inference_seconds:.2f}",
            flush=True,
        )
        if args.case_id:
            _write_jsonl(prediction_path, run_rows)

    # Preserve corpus order when a run is resumed in multiple batches.
    by_case = {row["case_id"]: row for row in run_rows}
    ordered_rows = [by_case[record["case_id"]] for record in _read_jsonl(args.corpus) if record["case_id"] in by_case]
    _write_jsonl(prediction_path, ordered_rows)

    metadata = {
        "model": model_name,
        "revision": revision,
        "gliner2_library": getattr(gliner2, "__version__", "unknown"),
        "torch": torch.__version__,
        "cuda_runtime": torch.version.cuda,
        "transformers": transformers.__version__,
        "python": platform.python_version(),
        "parameter_dtype": str(next(model.parameters()).dtype),
        "chunk_size": DEFAULT_CHUNK_SIZE,
        "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
        "labels": "app.services.requirement_extractor.MODEL_LABELS",
        "inference_arguments": {
            "include_confidence": True,
            "include_spans": True,
            "overlap_policy": "flat",
            "threshold": "not passed; GLiNER2 extract_entities default is 0.5",
        },
        "device": device,
        "gpu_available": bool(torch.cuda.is_available()),
        "load_seconds": round(load_seconds, 3),
        "first_inference_seconds": round(inference_times[0], 3) if inference_times else None,
        "warm_jobs_measured": max(0, len(inference_times) - 1),
        "warm_median_seconds": round(median(inference_times[1:]), 3) if len(inference_times) > 1 else None,
        "warm_total_seconds": round(sum(inference_times[1:]), 3),
        "rss_after_load_gib": rss_after_load_gib,
        "peak_rss_gib": _peak_rss_gib(),
        "jobs": len(ordered_rows),
        "jobs_measured_this_invocation": len(inference_times),
        "corpus_sha256": hashlib.sha256(args.corpus.read_bytes()).hexdigest(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
