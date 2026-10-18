# Architecture Decision Records

| 番号 | タイトル | ステータス |
|---|---|---|
| [0001](0001-ollama-on-k8s-cpu.md) | 推論基盤に Ollama を採用し、CPU 専用で Kubernetes 上に構築する | 採用 |
| [0002](0002-model-selection.md) | モデル選定方針 | 採用 (実測後に見直す) |
| [0003](0003-access-and-exposure.md) | アクセス方法と公開範囲 | 一部置き換え済み (ローカルアクセスは0005に置換、外部公開は保留) |
| [0004](0004-model-update-and-gitops.md) | モデルの自動更新と GitOps (ArgoCD) による管理 | 採用 |
| [0005](0005-lan-exposure-via-loadbalancer.md) | LAN 向けの公開に MetalLB の LoadBalancer (固定 IP) を使う | 採用 |

## 運用ルール
- 決定を変える場合は既存のADRを書き換えず、新しいADRを追加して旧ADRのステータスを「置き換え済み」に更新する。
- ただし、未検証事項が実測で確定した場合は、該当ADRの追記を許可する。
