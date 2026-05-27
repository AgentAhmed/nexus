# NEXUS Makefile — common commands
# Usage: make <command>

.PHONY: help setup dev test build deploy clean

help:
	@echo ""
	@echo "  NEXUS — Available commands"
	@echo ""
	@echo "  make setup      Install all dependencies"
	@echo "  make dev        Run locally (API + frontend)"
	@echo "  make api        Run API only"
	@echo "  make docker     Run everything with Docker"
	@echo "  make docker-free  Run with free-tier optimised settings"
	@echo "  make build      Build Docker images"
	@echo "  make clean      Remove temp files and cache"
	@echo "  make demo       Hit the demo endpoint"
	@echo ""

setup:
	@echo "Setting up NEXUS..."
	@cp -n .env.example .env 2>/dev/null && echo "Created .env — add your API keys!" || echo ".env already exists"
	pip install -r requirements.txt
	cd frontend && npm install
	@echo "Done! Run 'make dev' to start."

api:
	uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev

dev:
	@echo "Starting NEXUS locally..."
	@make api &
	@make frontend

docker:
	docker compose up -d
	@echo "NEXUS running at http://localhost"

docker-free:
	docker compose -f docker-compose.free.yml up -d
	@echo "NEXUS (free tier) running at http://localhost:8000"

docker-dev:
	docker compose -f docker-compose.dev.yml up

build:
	docker compose build

demo:
	curl -s -X POST http://localhost:8000/api/demo | python3 -m json.tool

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf frontend/.next frontend/node_modules 2>/dev/null || true
	@echo "Cleaned."

logs:
	docker compose logs -f api

restart:
	docker compose restart api
