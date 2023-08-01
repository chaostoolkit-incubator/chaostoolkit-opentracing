.PHONY: install
install:
	pip install --upgrade pip setuptools wheel
	pip install -r requirements.txt

.PHONY: install-dev
install-dev: install
	pip install -r requirements-dev.txt
	python setup.py develop

.PHONY: lint
lint:
	ruff chaostracing/ tests/
	isort --check-only --profile black chaostracing/ tests/
	black --check --diff chaostracing/ tests/

.PHONY: format
format:
	isort --profile black chaostracing/ tests/
	black chaostracing/ tests/
	ruff chaostracing --fix

.PHONY: tests
tests:
	pytest
