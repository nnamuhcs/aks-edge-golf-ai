.PHONY: help setup backend frontend build test verify deploy deploy-kind clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

backend: ## Run backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Build frontend (served by backend)
	cd frontend && npm run build

build: ## Build Docker images
	docker build -t golf-ai-backend:latest -f backend/Dockerfile backend/
	docker build -t golf-ai-frontend:latest -f frontend/Dockerfile frontend/

test: ## Run all tests
	cd backend && python -m pytest tests/ -v

verify: ## Run verify_and_fix loop
	bash scripts/verify_and_fix.sh

deploy: ## Deploy to Kubernetes (requires images built)
	kubectl apply -k deploy/base/

deploy-kind: ## Full Kind deployment (build, create cluster, load, deploy)
	$(MAKE) build
	kind create cluster --name golf-ai --config deploy/kind-config.yaml || true
	kind load docker-image golf-ai-backend:latest golf-ai-frontend:latest --name golf-ai
	kubectl apply -k deploy/base/
	@echo ""
	@echo "✅ App running at http://localhost:3001"

clean: ## Remove generated data
	rm -rf backend/data
	cd frontend && rm -rf node_modules dist
