# ADR-0004: モデルの自動更新と GitOps (ArgoCD) による管理

- ステータス: 採用
- 日付: 2026-10-18

## 背景
- モデルを常に最新に保ちたい。
- クラスタには ArgoCD が導入済みで、既存の chat-app も ArgoCD で管理している。
- GitHub のリポジトリは最初に push したブランチが既定ブランチになっており、`main` が存在しない。
- 運用ルールとして、`main` への直接 push・commit は行わず、フィーチャーブランチと PR を使う。

## 決定

### モデルの更新
- モデル一覧は `k8s/models.txt` に一本化する。kustomize の `configMapGenerator` で ConfigMap (`ollama-models-list`) にする。
- CronJob `model-updater` が毎週月曜 03:00 (JST) に、一覧の各モデルを `ollama pull` する。
  タグのダイジェストが変わっていれば差分を取得し、変わっていなければ数秒で終わる。
- Ollama の起動待ち (最大5分) を入れ、Pod の入れ替え中でも失敗しにくくする。
- 手動実行は `make update-models`。

### ArgoCD
- Application `local-llm` が `main` ブランチの `k8s/` を追跡する (`argocd/application.yaml`)。
- 自動同期 (prune、selfHeal) とする。モデル保存用 PVC は `Prune=false,Delete=false` で保護する。
- 変更は PR で `main` にマージして反映する。

## 限界
- タグを固定しているため、同じタグの更新 (パッチ・再量子化など) は追従するが、
  新しい世代 (例: `granite4.2` から `granite4.3`) への切り替えは自動では行われない。
  世代の更新は性能・サイズ・ライセンスが変わりうるため、`k8s/models.txt` を編集し、PR のレビューを経て行う。
- Ollama 本体のイメージ (`ollama/ollama:latest`) は、Pod の再作成時に取得される。固定はしていない。

## 結果・トレードオフ
- モデル一覧を変更すると、PR のマージ後に ArgoCD が ConfigMap を更新し、次回の定期実行で反映される。
  すぐに反映したい場合は `make update-models` を使う。
- 取得に失敗してもサービスは止まらない (既存のモデルはそのまま使える)。
- 週次の更新時は、ネットワークと Worker のディスクに一時的な負荷がかかる。
