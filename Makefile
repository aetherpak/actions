.DEFAULT_GOAL := help

.PHONY: setup test lint check clean help

##@ Bootstrap

setup: ## Install the pre-commit git hook
	uvx pre-commit install

##@ Build & Quality

test: ## Run the unit tests (pytest on Python 3.14 via uvx)
	uvx --python 3.14 pytest

lint: ## Run all pre-commit checks (ruff, yaml, formatting)
	uvx pre-commit run --all-files

check: test lint ## Run tests and lint (mirrors CI)

clean: ## Remove generated build, repo, and site artifacts
	rm -rf .flatpak-builder _build _repo _oci-image _site \
	  _repo_test _repo_test_oci _site_test \
	  tests/mock_repo tests/mock_contents
	find . -type d -name __pycache__ -exec rm -rf {} +

##@ Utilities

help: ## Show this help
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} \
	  /^[a-zA-Z0-9_/-]+:.*?##/ { printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2 } \
	  /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)
