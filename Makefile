.PHONY: help install test lint format clean run-tests setup-dev validate-all

# Default target
help:
	@echo "Extended OpenAI Conversation - Development Commands"
	@echo ""
	@echo "make install      - Install dependencies"
	@echo "make test         - Run all tests"
	@echo "make lint         - Run linting checks"
	@echo "make format       - Format code with black and isort"
	@echo "make clean        - Clean up cache and build files"
	@echo "make setup-dev    - Set up development environment"
	@echo "make validate-all - Run all validation checks"
	@echo "make run-tests    - Run the test runner script"

# Install dependencies
install:
	pip install -r requirements_test.txt
	pip install -e .
	pre-commit install

# Run tests
test:
	pytest -v

# Run linting
lint:
	ruff check .
	mypy custom_components/extended_openai_conversation
	black --check .
	isort --check-only .

# Format code
format:
	black .
	isort .
	ruff check --fix .

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf venv_test

# Set up development environment
setup-dev: clean
	python -m venv venv_test
	./venv_test/bin/pip install --upgrade pip
	./venv_test/bin/pip install -r requirements_test.txt
	./venv_test/bin/pip install -e .
	./venv_test/bin/pre-commit install

# Run all validation checks
validate-all: lint
	pre-commit run --all-files
	hassfest validate
	pytest --cov=custom_components.extended_openai_conversation

# Run the test runner script
run-tests:
	python run_tests.py
