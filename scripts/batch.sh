#!/usr/bin/env bash
# 時間のかかる問い合わせを K8s の Job として投入し、放置して後から結果を読む (ADR-0011)。
# Job はクラスタ側で動くため、手元の PC を閉じても止まらない。
#
#   scripts/batch.sh submit <プロンプトのファイル> [-m モデル] [-t 制限時間(時間)]
#   scripts/batch.sh list
#   scripts/batch.sh result <ID>
#   scripts/batch.sh logs <ID>
#   scripts/batch.sh cancel <ID>
set -euo pipefail

NAMESPACE="${NAMESPACE:-llm}"
DEPLOY="${DEPLOY:-ollama}"
MODEL_DEFAULT="${BATCH_MODEL:-gpt-oss:20b}"   # 放置実行向けに、遅いが品質の高いモデルを既定にする (ADR-0012)
HOURS_DEFAULT="${BATCH_HOURS:-12}"
RESULT_DIR="/root/.ollama/batch"   # Ollama Pod から見た結果の保存先 (PVC の batch/)
export KUBECONFIG="${KUBECONFIG:-$HOME/.kube/config-home}"

usage() { sed -n '2,10p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-1}"; }

submit() {
  local file="" model="$MODEL_DEFAULT" hours="$HOURS_DEFAULT"
  while [ $# -gt 0 ]; do
    case "$1" in
      -m) model="$2"; shift 2 ;;
      -t) hours="$2"; shift 2 ;;
      -*) usage ;;
      *) file="$1"; shift ;;
    esac
  done
  [ -n "$file" ] && [ -f "$file" ] || { echo "プロンプトのファイルを指定してください" >&2; usage; }
  [[ "$hours" =~ ^[0-9]+$ ]] || { echo "-t は時間の整数で指定してください" >&2; exit 1; }

  # ollama run は未取得のモデルを自動で pull してしまう。意図しない大容量の取得を避けるため、取得済みのものに限る
  if ! kubectl -n "$NAMESPACE" exec "deploy/$DEPLOY" -- ollama list | awk 'NR>1{print $1}' | grep -qxF "$model"; then
    echo "エラー: $model は Ollama に取得されていません (取得済み: scripts/pull-models.sh)" >&2
    exit 1
  fi

  # models.txt にないモデルは、メモリ制限を超えて Ollama が落ちる可能性がある (ADR-0006、ADR-0012)
  if ! grep -vE '^\s*(#|$)' "$(dirname "$0")/../k8s/models.txt" | sed 's/\s*#.*//' | grep -qxF "$model"; then
    echo "警告: $model は k8s/models.txt にありません。メモリ不足で Ollama が落ちる可能性があります。" >&2
  fi

  local id="batch-$(date +%Y%m%d-%H%M%S)"
  kubectl -n "$NAMESPACE" create configmap "$id" --from-file=prompt.txt="$file" >/dev/null

  # Job のマニフェスト。プレースホルダを置き換えて適用する
  sed -e "s/__ID__/$id/g" -e "s|__MODEL__|$model|g" -e "s/__DEADLINE__/$((hours * 3600))/g" <<'EOF' | kubectl -n "$NAMESPACE" apply -f - >/dev/null
apiVersion: batch/v1
kind: Job
metadata:
  name: __ID__
  labels:
    app: batch
  annotations:
    batch/model: "__MODEL__"
spec:
  backoffLimit: 0                  # 長い処理を黙って再実行しない
  activeDeadlineSeconds: __DEADLINE__
  ttlSecondsAfterFinished: 604800  # 終了後 7 日で Job と ConfigMap を消す。結果は PVC に残る
  template:
    spec:
      restartPolicy: Never
      nodeSelector:
        kubernetes.io/hostname: k8s-worker
      containers:
        - name: run
          image: ollama/ollama:latest
          env:
            - name: OLLAMA_HOST
              value: "http://ollama.llm.svc.cluster.local:11434"
            - name: BATCH_ID
              value: "__ID__"
            - name: MODEL
              value: "__MODEL__"
          command:
            - /bin/sh
            - -c
            - |
              set -u
              D=/batch
              i=0
              until ollama list >/dev/null 2>&1; do
                i=$((i + 1))
                [ "$i" -ge 60 ] && { echo "Ollama に接続できない"; exit 1; }
                sleep 5
              done
              start=$(date -Iseconds)
              ollama run --nowordwrap --hidethinking "$MODEL" < /in/prompt.txt > "$D/$BATCH_ID.out" 2> "$D/$BATCH_ID.err"
              rc=$?
              end=$(date -Iseconds)
              {
                echo "# $BATCH_ID"
                echo "- モデル: $MODEL"
                echo "- 開始: $start"
                echo "- 終了: $end"
                echo "- 終了コード: $rc"
                echo
                sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$D/$BATCH_ID.out"
                if [ "$rc" -ne 0 ]; then
                  echo
                  echo "## エラー出力"
                  sed 's/\x1b\[[0-9;?]*[a-zA-Z]//g' "$D/$BATCH_ID.err"
                fi
              } > "$D/$BATCH_ID.md.tmp"
              mv "$D/$BATCH_ID.md.tmp" "$D/$BATCH_ID.md"
              rm -f "$D/$BATCH_ID.out"
              [ -s "$D/$BATCH_ID.err" ] || rm -f "$D/$BATCH_ID.err"
              exit "$rc"
          volumeMounts:
            - { name: prompt, mountPath: /in, readOnly: true }
            - { name: models, mountPath: /batch, subPath: batch }
          resources:
            requests: { cpu: 50m, memory: 64Mi }
            limits: { memory: 256Mi }
      volumes:
        - name: prompt
          configMap:
            name: __ID__
        - name: models
          persistentVolumeClaim:
            claimName: ollama-models
EOF

  # ConfigMap を Job の子にして、Job の削除時に一緒に消えるようにする
  local uid
  uid="$(kubectl -n "$NAMESPACE" get job "$id" -o jsonpath='{.metadata.uid}')"
  kubectl -n "$NAMESPACE" patch configmap "$id" --type=merge \
    -p "{\"metadata\":{\"ownerReferences\":[{\"apiVersion\":\"batch/v1\",\"kind\":\"Job\",\"name\":\"$id\",\"uid\":\"$uid\"}]}}" >/dev/null

  echo "投入しました: $id (モデル: $model、制限時間: ${hours}時間)"
  echo "結果の確認: scripts/batch.sh result $id"
  echo "注意: Ollama は同時に 1 件ずつ処理するため、実行中は Continue のチャットも待たされます。"
}

list() {
  kubectl -n "$NAMESPACE" get jobs -l app=batch \
    -o custom-columns='ID:.metadata.name,モデル:.metadata.annotations.batch/model,実行中:.status.active,成功:.status.succeeded,失敗:.status.failed,開始:.status.startTime'
}

result() {
  local id="${1:?ID を指定してください}"
  if kubectl -n "$NAMESPACE" exec "deploy/$DEPLOY" -- test -f "$RESULT_DIR/$id.md" 2>/dev/null; then
    kubectl -n "$NAMESPACE" exec "deploy/$DEPLOY" -- cat "$RESULT_DIR/$id.md"
  else
    echo "結果はまだありません。Job の状態:" >&2
    kubectl -n "$NAMESPACE" get job "$id" >&2
    kubectl -n "$NAMESPACE" exec "deploy/$DEPLOY" -- sh -c "cat '$RESULT_DIR/$id.err' 2>/dev/null" >&2 || true
    exit 1
  fi
}

case "${1:-}" in
  submit) shift; submit "$@" ;;
  list) list ;;
  result) shift; result "$@" ;;
  logs) shift; kubectl -n "$NAMESPACE" logs "job/${1:?ID を指定してください}" ;;
  cancel) shift; kubectl -n "$NAMESPACE" delete job "${1:?ID を指定してください}" ;;
  *) usage 0 ;;
esac
