#!/usr/bin/env python3
"""Run Small or Base on the six frozen Convverge presentation variants."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
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


def _key(text: str) -> str:
    import re

    return " ".join(re.findall(r"[a-z0-9+#./]+", text.casefold()))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    args = parser.parse_args()

    import torch
    from gliner2 import AutoExtractor
    from huggingface_hub import snapshot_download

    model_name, revision = MODELS[args.model]
    device = args.device
    if device == "auto":
        device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda" and not torch.cuda.is_available():
        raise SystemExit("CUDA was requested but is not available")
    local_path = snapshot_download(model_name, revision=revision, local_files_only=args.local_files_only)
    model = AutoExtractor.from_pretrained(local_path, map_location=device).eval()
    runtime = GlinerRuntime(model=model, chunk_size=DEFAULT_CHUNK_SIZE, chunk_overlap=DEFAULT_CHUNK_OVERLAP)

    source_path = ROOT / "benchmarks/job-requirements/corpus/invariance/convverge-v1.jsonl"
    variants = [json.loads(line) for line in source_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    results: list[dict[str, Any]] = []
    baseline_keys: set[str] | None = None
    baseline_count: int | None = None
    for variant in variants:
        text = variant["text"]
        started = time.perf_counter()
        spans = runtime.extract_entities(text, MODEL_LABELS)
        elapsed = time.perf_counter() - started
        extracted = extract_requirements_from_entities(
            text,
            spans,
            extractor_version=f"{model_name}@{revision}+{SCANNER_EXTRACTOR_VERSION}",
        )
        units = [
            {
                "source_text": req.source.original_text,
                "importance": req.importance.value,
                "family": req.family.value,
                "start": req.source.source_start,
                "end": req.source.source_end,
            }
            for req in extracted.requirements
        ]
        keys = {_key(unit["source_text"]) for unit in units}
        if variant["variant"] == "original_bullets":
            baseline_keys = keys
            baseline_count = len(units)
        intersection = len(keys & (baseline_keys or set()))
        union = len(keys | (baseline_keys or set()))
        results.append(
            {
                "variant": variant["variant"],
                "source_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "raw_span_count": len(spans),
                "candidate_requirement_span_count": sum(span.label == "candidate_requirement" for span in spans),
                "final_requirement_count": len(units),
                "surface_text_jaccard_to_original": round(intersection / union, 4) if union else 1.0,
                "requirement_count_ratio_to_original": round(len(units) / baseline_count, 4) if baseline_count else None,
                "inference_seconds": round(elapsed, 3),
                "requirements": units,
            }
        )

    output_dir = ROOT / f"benchmarks/job-requirements/runs/invariance-gliner-{args.model}"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "convverge-v1.json").write_text(
        json.dumps(
            {
                "model": model_name,
                "revision": revision,
                "device": device,
                "chunk_size": DEFAULT_CHUNK_SIZE,
                "chunk_overlap": DEFAULT_CHUNK_OVERLAP,
                "default_threshold": 0.5,
                "corpus_sha256": hashlib.sha256(source_path.read_bytes()).hexdigest(),
                "variants": results,
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    for result in results:
        print(
            f"{result['variant']}: raw={result['raw_span_count']} "
            f"candidate_spans={result['candidate_requirement_span_count']} "
            f"final={result['final_requirement_count']} "
            f"surface_jaccard={result['surface_text_jaccard_to_original']} "
            f"count_ratio={result['requirement_count_ratio_to_original']} "
            f"seconds={result['inference_seconds']:.2f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
