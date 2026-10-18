# ADR-0003: アクセス方法と公開範囲

- ステータス: 一部置き換え済み (ローカルアクセスの方針は ADR-0005 に置き換え。外部公開は保留)
- 日付: 2026-10-18

## 背景
- まずローカルから VSCode で使えるようにしたい。
- 将来は Cloudflare Tunnel で外部からも呼び出したいが、一旦保留とした。
- Ollama には認証機能がない。

## 決定
- Service は **ClusterIP** を既定とし、`kubectl port-forward` (`make forward`) で `localhost:11434` に接続する。
- LAN 内の他端末から使う場合に限り、任意で NodePort (31434) を追加できる (`k8s/service-nodeport.yaml`、kustomization には含めない)。
- VSCode からは Continue 拡張で接続する (`docs/vscode-continue.md`)。チャットと補完に別モデルを割り当てる。
- Secret 類は git に含めない (`.gitignore`)。

## 保留事項: Cloudflare Tunnel による外部公開
実施する場合の方針を記録しておく。
- `cloudflared` を同一クラスタに 2 レプリカで配置し、`http://ollama.llm.svc.cluster.local:11434` へ転送する。外向き接続のみのため、ルーターのポート開放は不要。
- トンネルトークンは Secret として直接作成し、マニフェストや git に含めない。
- **Cloudflare Access による認証を必須とする**。プログラムからの利用は Service Token (`CF-Access-Client-Id` と `CF-Access-Client-Secret`) を使う。WAF のレート制限も併用する。
- 注意: Cloudflare 経由では、最初のレスポンスが 100 秒以内に返らないと 524 エラーになる。CPU 推論は長いプロンプトの処理に時間がかかるため、ストリーミングを有効にし、送るコンテキストを絞る。
- Ollama が 403 を返す場合は、`OLLAMA_ORIGINS` の設定か、Host ヘッダーの上書きを検討する。

## 結果・トレードオフ
- 認証がない Ollama を LAN の外へ出さないため、現時点の露出面は最小。
- port-forward は常時起動が必要で、手間が増える。常用する段階で LB や Ingress を検討する。
