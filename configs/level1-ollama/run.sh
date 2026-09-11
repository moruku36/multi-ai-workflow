#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME="qwen-processor"

echo "=== Building Level 1 Ollama Model: ${MODEL_NAME} ==="
cd "$(dirname "$0")"

# Modelfile からカスタムモデルを作成
ollama create "${MODEL_NAME}" -f ./Modelfile

echo "Model '${MODEL_NAME}' created successfully!"
echo "Usage example:"
echo "  cat data.log | ollama run ${MODEL_NAME} 'Extract all error messages as JSON array'"
