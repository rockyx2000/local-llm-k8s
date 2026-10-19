# local-llm-k8s

自宅 Kubernetes クラスタ上で、CPU 推論のローカル LLM (Ollama) を動かすための構成。
VSCode (Continue 拡張) から OpenAI 互換 / Ollama API で呼び出す。

- 対象環境: Ryzen 7 3700X、GPU なし、Worker VM は 6コア/12スレッド
- モデル方針: 中国系以外 (IBM Granite、BigCode StarCoder2、OpenAI gpt-oss など)

## 構成

```
k8s/        Kubernetes マニフェスト (kustomize)
scripts/    モデル取得スクリプトとモデル一覧
docs/       クライアント側の設定例
Makefile    よく使う操作
```

## 手順

```bash
make apply     # namespace / PVC / Deployment / Service を作成
make status    # Pod が Running になるまで待つ
make models    # k8s/models.txt のモデルを取得
make test      # 疎通確認 (LAN から http://10.0.1.200:11434 に接続できる)
make forward   # (任意) 手元に一時転送したい場合
```

VSCode の設定は `docs/vscode-continue.md` を参照。

## 放置して実行する (バッチ)

時間のかかる問い合わせは、K8s の Job として投入すれば、PC を閉じても止まらない (`docs/adr/0011-batch-jobs-for-unattended-runs.md`)。

```bash
scripts/batch.sh submit prompt.txt            # 投入 (モデルは -m、制限時間は -t 時間)
scripts/batch.sh list                         # 状態の一覧
scripts/batch.sh result <ID>                  # 結果を表示
scripts/batch.sh cancel <ID>                  # 取り消し
```

実行中は Ollama が占有されるため、Continue のチャットも待たされる。

## ArgoCD による管理

`argocd/application.yaml` を初回のみ手動で適用すると、以降は `k8s/` の変更が自動で反映される。

```bash
kubectl apply -f argocd/application.yaml
```

kubeconfig は `~/.kube/config-home` (microk8s の master から取得したもの) を使う。

## モデルの更新

`k8s/models.txt` の一覧を、CronJob (`model-updater`) が毎週月曜 03:00 (JST) に再取得して最新に保つ。
すぐに更新したい場合は `make update-models`。新しい世代へ切り替えるときは `k8s/models.txt` を編集して PR を出す
(詳細は `docs/adr/0004-model-update-and-gitops.md`)。

## 今後の予定
- Cloudflare Tunnel による外部公開 (Cloudflare Access での認証を併用する)

## 注意
- Ollama には認証がない。LAN 外へ公開する場合は必ず認証を前段に置く。
- Secret (トンネルトークン等) は git に含めない。`.gitignore` を参照。
