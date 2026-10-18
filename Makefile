# microk8s の kubeconfig (master から取得して配置したもの)
export KUBECONFIG ?= $(HOME)/.kube/config-home

NAMESPACE ?= llm
LOCAL_PORT ?= 11434

.PHONY: apply delete status models forward test logs

apply:      ## マニフェストを適用
	kubectl apply -k k8s/

delete:     ## リソースを削除 (PVC とモデルも消える点に注意)
	kubectl delete -k k8s/

status:     ## Pod / Service の状態を表示
	kubectl -n $(NAMESPACE) get pods,svc,pvc

models:     ## models.txt のモデルを取得
	bash scripts/pull-models.sh

forward:    ## ローカルから localhost:$(LOCAL_PORT) で接続できるようにする
	kubectl -n $(NAMESPACE) port-forward svc/ollama $(LOCAL_PORT):11434

test:       ## 疎通確認 (forward 実行中に別ターミナルで)
	curl -s http://localhost:$(LOCAL_PORT)/api/tags

logs:       ## Ollama のログを表示
	kubectl -n $(NAMESPACE) logs deploy/ollama -f
