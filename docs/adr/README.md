# Architecture Decision Records

| 番号 | タイトル | ステータス |
|---|---|---|
| [0001](0001-ollama-on-k8s-cpu.md) | 推論基盤に Ollama を採用し、CPU 専用で Kubernetes 上に構築する | 採用 |
| [0002](0002-model-selection.md) | モデル選定方針 | 一部置き換え済み (既定のチャットモデルは0006に置換) |
| [0003](0003-access-and-exposure.md) | アクセス方法と公開範囲 | 一部置き換え済み (ローカルアクセスは0005に置換、外部公開は保留) |
| [0004](0004-model-update-and-gitops.md) | モデルの自動更新と GitOps (ArgoCD) による管理 | 採用 |
| [0005](0005-lan-exposure-via-loadbalancer.md) | LAN 向けの公開に MetalLB の LoadBalancer (固定 IP) を使う | 採用 |
| [0006](0006-non-thinking-chat-models.md) | チャットモデルを thinking なしのものに変更し、メモリ制限を引き上げる | 一部置き換え済み (既定のチャットモデルは0007に置換。メモリ制限は0012で22Giに変更) |
| [0007](0007-lfm-main-and-qwen-completion.md) | メインのチャットに LFM2.5、補完に Qwen2.5-Coder を採用する | 一部置き換え済み (メインのチャットは0008に置換。補完の決定は有効) |
| [0008](0008-granite-main-chat-benchmark.md) | ベンチ結果に基づき、メインのチャットを granite4.1:8b に戻す | 採用 |
| [0009](0009-cpu-speedup-experiments.md) | CPU 推論の高速化の検証 (Ollama 設定、gpt-oss:20b、ik_llama.cpp) | 検証記録 (既定は変更しない。ik_llama.cpp は保留) |
| [0010](0010-context-length-8192.md) | Ollama のコンテキスト長を 8192 にする | 採用 |
| [0011](0011-batch-jobs-for-unattended-runs.md) | 時間のかかる問い合わせを K8s の Job で放置実行する | 採用 |
| [0012](0012-gpt-oss-for-batch.md) | gpt-oss:20b をバッチ用に採用し、Worker VM のメモリとメモリ制限を引き上げる | 採用 |

## 運用ルール
- 決定を変える場合は既存のADRを書き換えず、新しいADRを追加して旧ADRのステータスを「置き換え済み」に更新する。
- ただし、未検証事項が実測で確定した場合は、該当ADRの追記を許可する。
