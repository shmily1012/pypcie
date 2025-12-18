PYTHON ?= python3
VENV_DIR ?= .venv

.PHONY: venv test lint build clean

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(VENV_DIR)/bin/pip install -U pip
	$(VENV_DIR)/bin/pip install -e .[dev]

test:
	$(PYTHON) -m pytest -q

lint:
	@echo "No lint configured"

build:
	$(PYTHON) -m build

clean:
	rm -rf $(VENV_DIR) .pytest_cache build dist *.egg-info
