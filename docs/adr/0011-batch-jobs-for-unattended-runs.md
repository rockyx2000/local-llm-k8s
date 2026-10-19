# ADR-0011: 時間のかかる問い合わせを K8s の Job で放置実行する

- ステータス: 採用
- 日付: 2026-10-20

## 背景
- CPU 推論は遅く (granite4.1:8b で約 6.5 tokens/s、`gpt-oss:20b` は回答まで約 100 秒)、長い作業は放置したい。
- Continue は VSCode を開いたままの対話前提で、ウィンドウを閉じたりスリープしたりすると接続が切れて生成が止まる。

## 決定
- `scripts/batch.sh` で、プロンプトのファイルを K8s の Job として投入する。Job はクラスタ側で動くため、手元の PC を閉じても止まらない。
- 結果は PVC (`ollama-models`) の `batch/` に Markdown で保存する。`scripts/batch.sh result <ID>` が、Ollama Pod 経由で読み出す。
- 構成:
  - プロンプトは ConfigMap に入れ、Job の子にする (Job の削除時に一緒に消える)。
  - Job は Ollama の既存イメージ (`ollama/ollama`) の `ollama run` を使う。`--hidethinking` で推論モデルの思考を除く。
  - `backoffLimit: 0` (長い処理を黙って再実行しない)、制限時間は既定 12 時間 (`-t` で変更)、終了後 7 日で Job を削除する。結果ファイルは残る。
  - `k8s/` の kustomization には含めない。ArgoCD の管理対象外のため、selfHeal や prune の影響を受けない。
- 取得済みでないモデルは、投入時に拒否する。`ollama run` は未取得のモデルを自動で pull するため、タイプミスで大容量の取得が走るのを避ける。
- `k8s/models.txt` にないモデルは警告を出す。メモリ制限を超えて Ollama が落ちる可能性があるため。
  (`gpt-oss:20b` は ADR-0012 で `models.txt` に入り、メモリ制限が 22Gi になったため、警告の対象外。)

## 検証
実クラスタで確認した。
- 正常系: `granite4.1:8b` で短いプロンプトを投入し、約 20 秒で完了、結果が読めた。
- 失敗系: 存在しないモデルでは終了コード 1 となり、エラー出力が結果に残った。
- 取り消し: `cancel` で Job と ConfigMap が一緒に消えた。
- 未取得モデル: 投入時に拒否され、ConfigMap の残骸もなかった。
- 試験の資源と結果ファイルは削除済み。

## 検討した代替案
- Continue CLI (`cn -p`): 同じ `config.yaml` を読むヘッドレス実行がある。alpha 版で、Ollama での動作が未確認のため、今回は見送り。
- Claude Code と Ollama の Anthropic 互換 API: 動作はするが、CPU 推論では入力が長すぎて現実的でない。
- 結果を `kubectl logs` だけで残す: Pod の削除で消えるため、PVC に保存する方式にした。
- 結果専用の PVC を作る: モデルの PVC (40Gi) に余裕があり、Deployment を変更せずに読み出せるため、既存の PVC の `batch/` を使う。

## 限界・注意
- **Ollama は同時に 1 件 (`OLLAMA_NUM_PARALLEL=1`) しか処理しない**。バッチの実行中は Continue のチャットも待たされる。長い処理は夜間に投入する。
- Ollama の再起動 (ArgoCD の同期、モデルの更新ジョブなど) が実行中に起きると Job は失敗する。再実行は手動で行う。
- 単発の問い合わせ専用。ツールを繰り返し呼ぶエージェント型の作業はできない。
- コンテキスト長はサーバーの既定 (8192、ADR-0010) に従う。これを超える入力は切り捨てられる。
- 結果ファイルは自動では消えない。不要になったら Ollama Pod の `/root/.ollama/batch/` から手動で削除する。
