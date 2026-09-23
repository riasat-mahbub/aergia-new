#!/usr/bin/env python3
"""Run the NuExtract 1.5 Tiny model-card extraction format on Convverge."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
MODEL = "numind/NuExtract-1.5-tiny"
REVISION = "63e2e80c804d9c97f3f19a4aa25613e7beca83c9"
TEMPLATE = {
    "requirements": [
        {
            "source_text": "",
            "type": "",
            "importance": "",
            "concepts": [],
            "constraints": [],
            "alternatives": [],
        }
    ]
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-files-only", action="store_true")
    parser.add_argument("--max-new-tokens", type=int, default=4000)
    args = parser.parse_args()

    import torch
    import transformers
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer

    corpus = ROOT / "benchmarks/job-requirements/corpus/real-jds-v1.jsonl"
    record = next(
        json.loads(line)
        for line in corpus.read_text(encoding="utf-8").splitlines()
        if json.loads(line)["case_id"] == "convverge-junior-software-developer-v1"
    )
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_dir = snapshot_download(MODEL, revision=REVISION, local_files_only=args.local_files_only)
    load_started = time.perf_counter()
    tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(model_dir, trust_remote_code=True).to(device).eval()
    load_seconds = time.perf_counter() - load_started

    prompt = (
        "<|input|>\n### Template:\n"
        + json.dumps(TEMPLATE, indent=2, ensure_ascii=False)
        + "\n### Text:\n"
        + record["text"]
        + "\n\n<|output|>"
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=10_000).to(model.device)
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(
            **inputs,
            max_new_tokens=args.max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    elapsed = time.perf_counter() - started
    output_ids = generated[0, inputs["input_ids"].shape[1]:]
    response = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    try:
        parsed = json.loads(response)
        records = parsed.get("requirements") if isinstance(parsed, dict) else None
        schema_valid = isinstance(records, list) and all(
            isinstance(item, dict)
            and isinstance(item.get("source_text"), str)
            and isinstance(item.get("type"), str)
            and isinstance(item.get("importance"), str)
            and isinstance(item.get("concepts"), list)
            and isinstance(item.get("constraints"), list)
            and isinstance(item.get("alternatives"), list)
            for item in records
        )
    except json.JSONDecodeError:
        parsed = None
        records = []
        schema_valid = False

    oracle_path = ROOT / "benchmarks/job-requirements/oracle/convverge-v1.json"
    oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
    gold_source_texts = {item["source_text"].casefold() for item in oracle["requirements"]}
    valid_requirement_count = sum(
        item["source_text"].casefold() in gold_source_texts
        and item["type"].strip()
        and item["importance"].strip()
        for item in records
    ) if schema_valid else 0

    output_dir = ROOT / "benchmarks/job-requirements/runs/nuextract-tiny"
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "convverge-response.txt").write_text(response + "\n", encoding="utf-8")
    metadata = {
        "model": MODEL,
        "revision": REVISION,
        "transformers": transformers.__version__,
        "torch": torch.__version__,
        "python": platform.python_version(),
        "device": device,
        "dtype": str(next(model.parameters()).dtype),
        "generation": {"do_sample": False, "max_new_tokens": args.max_new_tokens},
        "template": TEMPLATE,
        "case_id": record["case_id"],
        "source_sha256": hashlib.sha256(record["text"].encode("utf-8")).hexdigest(),
        "load_seconds": round(load_seconds, 3),
        "inference_seconds": round(elapsed, 3),
        "generated_tokens": int(output_ids.shape[-1]),
        "schema_valid": schema_valid,
        "parsed_record_count": len(records) if schema_valid else None,
        "candidate_requirement_count_matched_to_seed_oracle": valid_requirement_count,
        "omitted_seed_requirements": len(oracle["requirements"]) - valid_requirement_count,
        "peak_rss_gib": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024 / 1024, 3),
        "corpus_sha256": hashlib.sha256(corpus.read_bytes()).hexdigest(),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(metadata, indent=2, ensure_ascii=False))
    print("response preview:", response[:1200].replace("\n", " "))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
