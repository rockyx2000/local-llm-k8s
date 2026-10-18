# microk8s の kubeconfig (master から取得して配置したもの)
export KUBECONFIG ?= $(HOME)/.kube/config-home

NAMESPACE ?= llm
LOCAL_PORT ?= 11434
OLLAMA_URL ?= http://10.0.1.200:11434

.PHONY: apply delete status models update-models forward test logs

apply:      ## マニフェストを適用
	kubectl apply -k k8s/

delete:     ## リソースを削除 (PVC とモデルも消える点に注意)
	kubectl delete -k k8s/

status:     ## Pod / Service の状態を表示
	kubectl -n $(NAMESPACE) get pods,svc,pvc

models:     ## models.txt のモデルを取得
	bash scripts/pull-models.sh

update-models: ## 定期更新ジョブを今すぐ実行 (最新のモデルを再取得)
	kubectl -n $(NAMESPACE) create job --from=cronjob/model-updater model-updater-manual-$$(date +%s)

forward:    ## ローカルから localhost:$(LOCAL_PORT) で接続できるようにする
	kubectl -n $(NAMESPACE) port-forward svc/ollama $(LOCAL_PORT):11434

test:       ## 疎通確認 (LoadBalancer の IP に接続)
	curl -s $(OLLAMA_URL)/api/tags

logs:       ## Ollama のログを表示
	kubectl -n $(NAMESPACE) logs deploy/ollama -f
