# Atalhos de desenvolvimento do SecurePass (GNU Make).
# No Windows sem Make, consulte a seção "Comandos do Makefile" do README.

PYTHON ?= python
HOST ?= 127.0.0.1
PORT ?= 8000
SOURCES := app tests

.PHONY: install run test format lint

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.main:app --reload --host $(HOST) --port $(PORT)

test:
	$(PYTHON) -m pytest --cov --cov-report=term-missing

format:
	$(PYTHON) -m black $(SOURCES)

lint:
	$(PYTHON) -m ruff check $(SOURCES)
	$(PYTHON) -m black --check $(SOURCES)
