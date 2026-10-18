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
- 実環境の確認結果 (2026-10-18): microk8s v1.32、2ノード (`k8s-master` 10.0.1.101、`k8s-worker` 10.0.1.102)。
  Worker は 6 vCPU、メモリ約 30GB で、ArgoCD、chat-app、PostgreSQL、ingress、MetalLB などが同居している。
  StorageClass は `microk8s-hostpath` (既定、WaitForFirstConsumer)。MetalLB と ingress アドオンが有効。
- 上記を踏まえ、Pod は `kubernetes.io/hostname: k8s-worker` に固定し、リソースは requests が cpu 3 / memory 8Gi、
  limits が cpu 5 / memory 20Gi とした。他のワークロードを圧迫しないためで、推論スレッド数も 6 を超えない範囲に抑える。
- 障害の記録 (2026-10-18): 推論テスト中に Worker VM (Proxmox VM 104) が停止した。ホストの `dmesg` に
  `Out of memory: Killed process (kvm)` があり、ホストの OOM Killer が原因と確定した。
  ホストの物理メモリは 31GiB で、VM 104 に 30GiB を割り当てており、他の VM と合わせて物理メモリを超えていた。
  対処として VM 104 を 16GiB に減らし (Ballooning 無効)、Ollama の limits.memory を 10Gi に下げる。
- 性能上の問題: Proxmox の CPU タイプが `x86-64-v2-AES` で、VM から AVX/AVX2/FMA/F16C が見えていなかった
  (`/proc/cpuinfo` で確認、sse4_2 まで)。`host` に変更して AVX2 を有効にする。
- メモリ 16GiB では `gpt-oss:20b` (約14GB) は載らない。使う場合はホストの物理メモリ増設か他 VM の縮小が前提となる。
- hostpath の PVC は Worker のローカルディスク (空き約 100GB) に作られる。Worker 障害時はモデルの再取得が必要になる。
