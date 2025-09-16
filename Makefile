# Makefile for Partnerzy w Zbrodni - Demo Tools

.PHONY: help demo-up demo-images demo-tts demo-music demo-orchestrate demo-case-zero demo-admin-logs demo-all demo-run demo-clean clean-demo

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

demo-up: ## Start all services for demo
	@echo "Starting services for demo..."
	docker-compose up -d
	@echo "Services started."

demo-images: ## Generate demo images using local MPS SD
	@echo "Generating demo images..."
	python tools/seed_demo_images.py

demo-tts: ## Generate demo TTS samples
	@echo "Generating demo TTS samples..."
	python tools/seed_demo_tts.py

demo-music: ## Generate demo music through orchestrator
	@echo "Generating demo music..."
	python tools/seed_demo_music.py

demo-orchestrate: ## Run full orchestration demos
	@echo "Running orchestration demos..."
	python tools/seed_demo_orchestrate.py

demo-case-zero: ## Generate TTS for Case Zero scenario
	@echo "Generating TTS for Case Zero..."
	python tools/seed_case_zero_tts.py

demo-admin-logs: ## Seed fake admin logs
	@echo "Seeding admin logs..."
	python tools/seed_admin_fake_logs.py

demo-all: ## Run all demo seeding scripts
	@echo "Running all demo seeding scripts..."
	python tools/seed_all.py

demo-run: ## Run automated demo (SP + MP + Override + PDF)
	@echo "Running automated demo..."
	python tools/run_demo_automated.py

demo-clean: ## Clean demo files and reports
	@echo "Cleaning demo files..."
	rm -f Runbook_Demo_Report.pdf || true
	rm -rf data/images/generated/*.png
	rm -rf data/audio/*.wav
	rm -rf data/music/*.mp3
	@echo "Demo files cleaned."

clean-demo: ## Clean generated demo files
	@echo "Cleaning demo files..."
	rm -rf data/images/generated/*.png
	rm -rf data/audio/*.wav
	rm -rf data/music/*.mp3
	@echo "Demo files cleaned."

dev-setup: ## Setup development environment
	@echo "Setting up development environment..."
	pip install -r requirements-dev.txt
	@echo "Development environment ready."

services-up: ## Start all services
	@echo "Starting services..."
	docker-compose up -d
	@echo "Services started."

services-down: ## Stop all services
	@echo "Stopping services..."
	docker-compose down
	@echo "Services stopped."

services-restart: ## Restart all services
	@echo "Restarting services..."
	docker-compose restart
	@echo "Services restarted."

test: ## Run tests
	@echo "Running tests..."
	pytest -q

test-demo: ## Run demo-specific tests
	@echo "Running demo tests..."
	pytest -q -m "not llm and not suno"

web-client: ## Start web client
	@echo "Starting web client..."
	cd web_client && npm run dev

local-sd: ## Start local SD service (MPS)
	@echo "Starting local SD service..."
	uvicorn fastapi_mps_sd:app --host 0.0.0.0 --port 8501

smoke-providers: ## Test real media providers (images, TTS, music)
	@echo "Testing providers..."
	python tools/smoke_providers.py

smoke-swap: ## Test two-gear image swap (library -> generated)
	@echo "Testing image swap..."
	python tools/smoke_image_swap.py

shot-smoke: ## Test shot planner mapping
	@echo "Testing shot planner..."
	python tools/test_shot_planner.py

ui-guard: ## Test UI guardrails with Playwright
	@echo "Testing UI guardrails..."
	cd web_client && npx playwright test tests/ui_guardrails.spec.ts --headed --project=chromium

ui-nl: ## Test UI free-form NL with Playwright
	@echo "Testing UI free-form NL..."
	cd web_client && npx playwright test tests/ui_nl_freeform.spec.ts --headed --project=chromium

demo-sfx: ## Generate SFX files
	@echo "Generating SFX files..."
	python3 tools/seed_sfx.py

ui-relations: ## Test UI relations and SFX with Playwright
	@echo "Testing UI relations and SFX..."
	cd web_client && npx playwright test tests/ui_relations_sfx.spec.ts --headed --project=chromium
