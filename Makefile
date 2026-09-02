.PHONY: install dev-install test lint format typecheck check clean

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e .

dev-install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -v

lint:
	$(PYTHON) -m ruff check src/ tests/ examples/

format:
	$(PYTHON) -m ruff format src/ tests/ examples/

format-check:
	$(PYTHON) -m ruff format --check src/ tests/ examples/

typecheck:
	$(PYTHON) -m mypy src/

check: lint format-check typecheck test

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
