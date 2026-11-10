PYTHON ?= python3

.PHONY: run test
run:
	$(PYTHON) pipeline.py

test:
	$(PYTHON) -m pytest -q
