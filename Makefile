.PHONY: help setup demo-content backend frontend build test verify deploy clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	cd backend && pip install -r requirements.txt
	cd frontend && npm install

demo-content: ## Generate synthetic demo videos and reference frames
	cd scripts && python generate_demo_content.py

backend: ## Run backend dev server
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend: ## Run frontend dev server
	cd frontend && npm run dev

build: ## Build Docker images
	docker build -t golf-swing-ai-backend ./backend
	docker build -t golf-swing-ai-frontend ./frontend

test: ## Run all tests
	cd backend && python -m pytest tests/ -v

verify: ## Run verify_and_fix loop
	bash scripts/verify_and_fix.sh

deploy: ## Deploy to Kubernetes
	kubectl apply -k deploy/overlays/demo

deploy-local: ## Run with docker-compose
	docker-compose up --build

port-forward: ## Port-forward K8s services for local access
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	kubectl -n golf-ai port-forward svc/golf-backend 8000:8000 &
	kubectl -n golf-ai port-forward svc/golf-frontend 3000:80

clean: ## Remove generated data
	rm -rf backend/data sample_videos/*.mp4
	cd frontend && rm -rf node_modules dist
