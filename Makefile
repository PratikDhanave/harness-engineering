# harness-engineering — one-command workflows (tooling: uv; see CLAUDE.md)
.DEFAULT_GOAL := help
SHELL := /bin/bash

.PHONY: help setup model install test run run-local demo clean

help: ## list available targets
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-10s\033[0m %s\n", $$1, $$2}'

setup: ## install uv if needed, then dependencies + verify (macOS/Linux)
	./scripts/install.sh

model: ## pre-download the on-device model (~2-3 GB, one time)
	uv run python3 scripts/prefetch_model.py

install: ## provision Python (>=3.11) + all deps with uv
	uv sync --extra dev

test: ## run the full deterministic, cloud-free suite
	uv run --extra dev pytest -q

run: ## serve the API on :8000 (stub agent — no cloud needed)
	uv run uvicorn harness.app:app --reload

run-local: ## serve /chat via Agent Framework on Foundry Local (on-device; first /chat downloads the model)
	uv run uvicorn harness.app:app --reload --env-file .env

demo: ## end-to-end demo: guarded /chat (incl. obfuscated injection) + durable crash-resume
	@bash scripts/demo.sh

clean: ## remove local checkpoint store and caches
	rm -rf .harness .pytest_cache
