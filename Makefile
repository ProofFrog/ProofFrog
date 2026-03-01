PYTHON := .venv/bin/python

.PHONY: lint format test

lint:
	$(PYTHON) -m black --check proof_frog
	$(PYTHON) -m mypy proof_frog --no-warn-unused-ignores
	$(PYTHON) -m pylint proof_frog

format:
	$(PYTHON) -m black proof_frog

test:
	$(PYTHON) -m pytest
