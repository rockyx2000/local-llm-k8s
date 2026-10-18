# VSCode (Continue 拡張) から使う

事前に `make forward` を実行して `localhost:11434` で接続できる状態にする。
NodePort を使う場合は `apiBase` を `http://<ノードIP>:31434` に置き換える。

`~/.continue/config.yaml` の例:

```yaml
name: local-llm
version: 0.0.1
schema: v1
models:
  - name: Granite 4.2 8B (local)
    provider: ollama
    model: granite4.2:8b
    apiBase: http://localhost:11434
    roles: [chat, edit, apply]
  - name: StarCoder2 3B (local)
    provider: ollama
    model: starcoder2:3b
    apiBase: http://localhost:11434
    roles: [autocomplete]
```

## 補足
- CPU 推論は初回のロードと長いプロンプトの処理に時間がかかる。
  補完モデルは小さく保ち、チャットに渡すコンテキストは絞る。
- `OLLAMA_KEEP_ALIVE` により、一度ロードしたモデルは30分メモリに保持される。
