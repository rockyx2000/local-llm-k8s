#!/usr/bin/env bash
# k8s/models.txt に書かれたモデルを稼働中の Ollama Pod に取得させる。
set -euo pipefail

NAMESPACE="${NAMESPACE:-llm}"
DEPLOY="${DEPLOY:-ollama}"
MODELS_FILE="$(cd "$(dirname "$0")/../k8s" && pwd)/models.txt"

# コメントと空行を除いてモデル名を1つずつ pull する
grep -vE '^\s*(#|$)' "$MODELS_FILE" | sed 's/\s*#.*//' | while read -r model; do
  echo "==> pull: ${model}"
  kubectl -n "$NAMESPACE" exec "deploy/${DEPLOY}" -- ollama pull "$model"
done

echo "==> 取得済みモデル"
kubectl -n "$NAMESPACE" exec "deploy/${DEPLOY}" -- ollama list
