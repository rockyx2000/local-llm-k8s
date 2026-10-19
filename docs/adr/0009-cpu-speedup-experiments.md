# ADR-0009: CPU 推論の高速化の検証 (Ollama 設定、gpt-oss:20b、ik_llama.cpp)

- ステータス: 検証記録 (既定の構成は変更しない。ik_llama.cpp は未完成のため保留)
- 日付: 2026-10-20

## 背景
- 記事 (https://zenn.dev/ashidan/articles/tech_llm_cpu_b) が、CPU 推論の高速化として ik_llama.cpp、
  スレッドの固定、MoE モデルの利用を紹介していた。
- 現状の `granite4.1:8b` は、プロンプト処理 (pp) が約 25 tokens/s、生成 (tg) が約 6.5 tokens/s と遅い。
  ADR-0008 のとおり、dense 8B は生成がメモリ帯域で決まる。
- 次の 3 点を検証した。いずれも Worker VM (6 vCPU、20GiB) の実クラスタで、同じ GGUF を使った。

## 計測方法
- 速度 (Ollama): `ollama run --verbose` で、入力 約2100〜2500 トークンの長い入力 (pp) と短い入力 (tg) を各 2 回。
  プロンプトキャッシュを避けるため、先頭に毎回違う文字列を付けた。
- 速度 (ik_llama.cpp): `llama-bench -p 2048 -n 64 -fa 1 -rtr`。Ollama が取得済みの blob を読み取り専用で使用。
- 品質: `bench/` (4 課題 × 2 回) を `MODELS=gpt-oss:20b` で実行。ADR-0008 と同じ条件。
- 計測中は ArgoCD の自動同期を一時停止し、終了後に元へ戻した。リポジトリの manifest は変更していない。

## 結果

### 1. Ollama の設定 (Flash Attention、KV キャッシュの量子化)
| 設定 | pp | tg |
|---|---|---|
| 変更前 | 25.5 tokens/s | 6.4〜6.5 tokens/s |
| `OLLAMA_FLASH_ATTENTION=1` と `OLLAMA_KV_CACHE_TYPE=q8_0` | 18.0 tokens/s (悪化) | 6.4 tokens/s |
| `OLLAMA_FLASH_ATTENTION=1` のみ | 25.3 tokens/s | 6.4〜6.5 tokens/s |

- Flash Attention は効果がなく、KV キャッシュの q8_0 は pp を約 3 割悪化させた。どちらも採用しない。

### 2. MoE モデル `gpt-oss:20b` (Ollama)
メモリ制限を 17Gi に上げて計測した (14Gi では、約 13GB のモデルと KV キャッシュが収まらない)。

| 指標 | `granite4.1:8b` | `gpt-oss:20b` |
|---|---|---|
| pp | 25.5 tokens/s | 44.4 tokens/s (約 1.7 倍) |
| tg | 6.5 tokens/s | 8.9 tokens/s (約 1.4 倍) |
| バグ修正 | 満点 2/2 | 満点 2/2 |
| 仕様から実装 | 満点 0/2 (20/22、18/22) | 満点 2/2 (22/22、22/22) |
| リファクタ | 満点 0/2 (97/300、41/300) | 満点 2/2 (300/300、300/300) |
| テスト生成 | 0/2 (うち 1 回は 2/3) | 0/2 (2/3、2/3) |
| 応答までの時間の中央値 | 約 26 秒 | 約 100 秒 (最大 234 秒) |

- 品質は明確に上がった。ADR-0008 で両モデルが見落とした、リファクタの隠れた仕様 (奇数で 10 以下の要素は捨てる) も、2 回とも保てた。
- 推論モデルのため応答が長く、速度が上がっても、回答までの時間は Granite の約 4 倍かかる。ADR-0006 の問題が再発する。
- 約 13GB のため、補完モデル (約 2.5GB) と同時にロードすると、Worker VM (20GiB) の余裕が小さい。

### 3. ik_llama.cpp (cpu-full イメージ、`llama-bench`)
| モデル | pp | tg | 出力の正しさ |
|---|---|---|---|
| `granite4.1:8b` | 43.7 tokens/s (Ollama の約 1.7 倍) | 8.1 tokens/s (約 1.25 倍) | 壊れている |
| `gpt-oss:20b` | 92.0 tokens/s (Ollama の約 2.1 倍) | 11.2〜11.6 tokens/s (約 1.3 倍) | 素の補完は正常。チャットは壊れる |
| `lfm2.5:8b` | - | - | blob の読み込みに失敗 |

- `gpt-oss:20b` の tg はスレッド数 4〜5 で最大になった (3 で 10.9、4 で 11.6、5 で 11.6、6 で 11.2 tokens/s)。
- `llama-bench` は速度しか測らないため、最初は成功に見えた。実際に生成させて初めて問題が分かった。
- `granite4.1:8b`: 出力が空白になる。`-fa` や `-rtr` を外しても同じで、Granite 4.x のハイブリッド構造を正しく扱えていないと判断した。
  ik_llama.cpp の README にも Granite 4 の記載はない。
- `gpt-oss:20b`: Ollama の GGUF にはチャットテンプレートが入っておらず、`llama-server --jinja` が chatml にフォールバックする。
  `/v1/chat/completions` の応答は同じ文の繰り返しになり、ツール呼び出しも返らなかった。
  `--chat-template-file` で gpt-oss 用の jinja テンプレートを渡す必要があるが、未検証。
- `llama-server` のプロンプトキャッシュの既定が 8192MiB で、コンテナのメモリ制限と並ぶ。`--cache-ram` で小さくする必要がある。
- `llama-cli` や `llama-server` でコンテキスト長 (`-c`) を指定しないと、学習時の長さで KV キャッシュが確保され、17Gi でも OOMKilled になった。

## 決定
- Ollama の設定 (Flash Attention、KV キャッシュの量子化) は採用しない。
- 既定のチャットは `granite4.1:8b` のまま変更しない (ADR-0008)。`gpt-oss:20b` を既定にしない理由は、応答までの時間と、メモリ余裕の小ささ。
- `gpt-oss:20b` は、難しい課題向けの任意の選択肢とする。使う場合は、Ollama のメモリ制限を 16〜17Gi に上げ、補完モデルを同時にロードしない。
- ik_llama.cpp は、現時点では導入しない。`k8s/ik-llama.yaml` は未完成の実験用として残し、`kustomization.yaml` には含めない。
- `bench/bench.py` は、環境変数 `MODELS` でモデルを指定できるようにした。

## 未検証・次の候補
- ik_llama.cpp の `gpt-oss:20b` に `--chat-template-file` を渡し、チャットとツール呼び出しが正しく動くかの確認。
  動けば、pp 約 90、tg 約 11.5 tokens/s の見込み。ただし推論モデルなので、応答までの時間は 1 分前後と予想される。
- Granite を ik_llama.cpp で動かすには、対応版を待つ必要がある。
- Worker VM のメモリを 20GiB から増やす (ホストの物理メモリは 31GiB)。`gpt-oss:20b` と補完モデルを同時に置くために必要。
- ik_llama.cpp の MetalLB 用 IP (`10.0.1.201`) は未確認。有効化の前に ping と ARP で確認する (ADR-0005)。
- `k8s/ik-llama.yaml` のイメージは、動作確認後にタグではなくダイジェストで固定する。

## 限界・注意
- 品質の計測は各課題 2 回で、傾向を示すにとどまる (ADR-0008 と同じ)。
- Ollama の速度は `ollama run` の実測 (cpu limit 5)、ik_llama.cpp は `llama-bench` の合成ベンチ (cpu limit 6) で、条件が完全には揃っていない。
  実アプリ経由では、ik_llama.cpp の数値はやや低くなる見込み。
- 記事の環境 (Windows、Ryzen 5 5600G、DDR4 デュアルチャネル) とは異なる。`KMP_BLOCKTIME` と `OMP_PLACES` は Ollama では使えないため試していない。
