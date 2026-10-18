# VSCode (Continue 拡張) から使う

LAN 内の端末から `http://10.0.1.200:11434` に直接接続できる (MetalLB の固定 IP、ADR-0005)。
疎通確認は `curl http://10.0.1.200:11434/api/tags`。
なお Ollama には認証がないため、信頼できる LAN 内に限って使う。

手元から一時的に確認したいだけなら `make forward` で `localhost:11434` に転送してもよい。

`~/.continue/config.yaml` の例:

```yaml
name: local-llm
version: 0.0.1
schema: v1
models:
  - name: Granite 4.2 8B (local)
    provider: ollama
    model: granite4.2:8b
    apiBase: http://10.0.1.200:11434
    roles: [chat, edit, apply]
  - name: StarCoder2 3B (local)
    provider: ollama
    model: starcoder2:3b
    apiBase: http://10.0.1.200:11434
    roles: [autocomplete]
```

## 補足
- CPU 推論は初回のロードと長いプロンプトの処理に時間がかかる。
  補完モデルは小さく保ち、チャットに渡すコンテキストは絞る。
- `OLLAMA_KEEP_ALIVE` により、一度ロードしたモデルは30分メモリに保持される。
