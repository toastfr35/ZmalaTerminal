PYTHON ?= python3
NODE ?= node

.PHONY: requirements requirements-check
requirements:
	$(PYTHON) build_tools/requirements.py

requirements-check:
	$(PYTHON) build_tools/requirements.py --check

test-llt:
	$(PYTHON) -m unittest discover -s tests/terminal/LLT -t .

test-hlt:
	$(PYTHON) -m unittest discover -s tests/terminal/HLT -t .

test-hlt-display:
	$(PYTHON) build_tools/run_display_hlt.py

test-adhoc:
	$(PYTHON) -m unittest discover -s tests/adhoc -t .

lint:
	$(PYTHON) -m ruff check .

package:
	$(PYTHON) build_tools/linux/package-terminal.py

leaflets:
	$(PYTHON) build_tools/leaflet/generate.py --language all --bundle
