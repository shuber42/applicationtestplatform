.PHONY: help install install-dev migrate runserver test lint format check clean

PYTHON ?= python3
PIP ?= $(PYTHON) -m pip
MANAGE := $(PYTHON) manage.py

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install runtime dependencies
	$(PIP) install -r requirements.txt

install-dev:  ## Install runtime + development dependencies
	$(PIP) install -r requirements-dev.txt

migrate:  ## Apply database migrations
	$(MANAGE) migrate

runserver:  ## Start the Django development server
	$(MANAGE) runserver

test:  ## Run the test suite
	$(PYTHON) -m pytest

lint:  ## Lint the codebase
	$(PYTHON) -m ruff check .

format:  ## Auto-format the codebase
	$(PYTHON) -m ruff format .

check:  ## Run Django's system checks
	$(MANAGE) check

clean:  ## Remove build and cache artifacts
	rm -rf .pytest_cache .ruff_cache .mypy_cache htmlcov coverage.xml \
		build dist *.egg-info __pycache__
	find . -type d -name '__pycache__' -exec rm -rf {} +
