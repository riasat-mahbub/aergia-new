#!/usr/bin/env bash
set -euo pipefail

# Build a production-derived benchmark image, then run it under explicit CPU
# and memory limits.  The model is downloaded while building the ephemeral
# image, so runtime load measurements do not include an accidental Hub fetch.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
base_image="${GLINER2_BASE_IMAGE:-aergia-api:gliner2-spike-base}"
spike_image="${GLINER2_SPIKE_IMAGE:-aergia-api:gliner2-spike}"
model="${GLINER2_MODEL:-fastino/gliner2.5-small-v1}"
revision="${GLINER2_MODEL_REVISION:-}"
torch_version="${GLINER2_TORCH_VERSION:-2.9.1+cpu}"
transformers_version="${GLINER2_TRANSFORMERS_VERSION:-4.51.3}"
memory="${GLINER2_MEMORY:-1g}"
cpus="${GLINER2_CPUS:-1}"
repeat="${GLINER2_REPEAT:-2}"
mode="${GLINER2_MODE:-hybrid}"

docker build \
  --file "$repo_root/api/Dockerfile" \
  --tag "$base_image" \
  "$repo_root"

docker build \
  --file "$repo_root/api/Dockerfile.gliner2-spike" \
  --tag "$spike_image" \
  --build-arg "BASE_IMAGE=$base_image" \
  --build-arg "GLINER2_MODEL=$model" \
  --build-arg "GLINER2_MODEL_REVISION=$revision" \
  --build-arg "TORCH_VERSION=$torch_version" \
  --build-arg "TRANSFORMERS_VERSION=$transformers_version" \
  "$repo_root"

args=(
  --fixtures /app/scripts/gliner2_jobs.json
  --model "$model"
  --mode "$mode"
  --repeat "$repeat"
)

docker run --rm \
  --cpus "$cpus" \
  --memory "$memory" \
  --memory-swap "$memory" \
  --env OMP_NUM_THREADS=1 \
  --env MKL_NUM_THREADS=1 \
  --env TOKENIZERS_PARALLELISM=false \
  "$spike_image" \
  "${args[@]}" \
  "$@"
