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
  - name: Granite 4.1 8B (メイン)
    provider: ollama
    model: granite4.1:8b
    apiBase: http://10.0.1.200:11434
    roles: [chat, edit, apply]
  - name: LFM2.5 8B (速い下書き用)
    provider: ollama
    model: lfm2.5:8b
    apiBase: http://10.0.1.200:11434
    roles: [chat]
  - name: Qwen2.5-Coder 3B (補完)
    provider: ollama
    model: qwen2.5-coder:3b
    apiBase: http://10.0.1.200:11434
    roles: [autocomplete]
```

## 補足
- 普段は `granite4.1:8b` を使う。LFM2.5 は速いが出力のバラつきが大きく、壊れたコードを出すことがあるため、下書きや雑談に限る (ADR-0008)。
- `lfm2.5:8b` は thinking を持ち、`<think>` タグの思考テキストが出力に混ざることがある。27 tokens/s のため待ち時間は小さい。
- `granite4.2` のような推論モデルは、Continue から thinking を止められず1回の応答に約2分かかるため使わない (ADR-0006)。
- CPU 推論は初回のロードと長いプロンプトの処理に時間がかかる。
  補完モデルは小さく保ち、チャットに渡すコンテキストは絞る。
- `OLLAMA_KEEP_ALIVE` により、一度ロードしたモデルは30分メモリに保持される。
