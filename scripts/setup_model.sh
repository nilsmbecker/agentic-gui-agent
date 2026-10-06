#!/usr/bin/env bash
# Download GELab-Zero-4B-preview from Hugging Face and register it in local Ollama.
# Follows third_party/gelab-zero/README.md (Step 1.2).
#
#   bash scripts/setup_model.sh          # q8_0 (~4.4 GB, recommended on 18 GB Macs)
#   QUANT=f16 bash scripts/setup_model.sh
#
# Weights land in models/ (gitignored via models/.gitignore).
set -euo pipefail
cd "$(dirname "$0")/.."

NAME="gelab-zero-4b-preview"
QUANT="${QUANT:-q8_0}"
DIR="models/$NAME"

command -v ollama >/dev/null || { echo "Install Ollama first: https://ollama.com/download"; exit 1; }
command -v hf >/dev/null || python -m pip install -q huggingface_hub

mkdir -p models
hf download --no-force-download stepfun-ai/GELab-Zero-4B-preview --local-dir "$DIR"

cd "$DIR"
if [ "$QUANT" = "f16" ]; then
  ollama create "$NAME" -f Modelfile
else
  ollama create -q "$QUANT" "$NAME" -f Modelfile
fi
ollama list | grep "$NAME"
echo "Model ready. LLM_MODEL=$NAME in .env"
