# ADR-0001: 推論基盤に Ollama を採用し、CPU 専用で Kubernetes 上に構築する

- ステータス: 採用
- 日付: 2026-10-18

## 背景
- 自宅の Kubernetes (microk8s または minikube) 上にローカル LLM を立て、VSCode から呼び出したい。
- ハードウェアは Ryzen 7 3700X (Zen 2、AVX2 あり、AVX512 なし)、GPU は GT710 で推論には使えない。
- Worker VM は 6コア/12スレッド。master は低スペック。
- メモリ量と Kubernetes の種類は未確定。

## 決定
- 推論エンジンは **Ollama** とする。
- CPU のみで動かす。Worker 1台に Deployment を1レプリカ置く (`strategy: Recreate`)。
- モデルは RWO の PVC に保存する。
- 構成は kustomize と Makefile で管理する。

## 検討した代替案
- llama.cpp の `llama-server`: 細かいチューニングができるが、モデル管理を自前で行う必要がある。まず手軽さを優先し、必要になったら移行する。
- vLLM など GPU 前提の基盤: GPU がないため対象外。

## 結果・トレードオフ
- OpenAI 互換 API と Ollama API の両方が使え、Continue 拡張から直接接続できる。
- Ollama には認証機能がない。公開範囲の制御は別途行う (ADR-0003)。
- CPU 推論はメモリ帯域が律速になる。並列数は 1 に抑え (`OLLAMA_NUM_PARALLEL=1`)、モデルは 30 分保持する (`OLLAMA_KEEP_ALIVE`)。
- Worker のメモリ上限 (`limits.memory: 24Gi`) は仮置き。実メモリ量の確認後に調整する。
