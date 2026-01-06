.PHONY: help install install-dev test lint format clean build upload

help:
	@echo "Available commands:"
	@echo "  install      Install the package in development mode"
	@echo "  install-dev  Install with development dependencies"
	@echo "  test         Run tests"
	@echo "  lint         Run linting checks"
	@echo "  format       Format code with black"
	@echo "  clean        Clean build artifacts"
	@echo "  build        Build distribution packages"
	@echo "  upload       Upload to PyPI (requires credentials)"

install:
	pip install -e .

install-dev:
	pip install -e .
	pip install -r requirements-dev.txt

test:
	pytest tests/ -v --cov=mcp_manager

lint:
	flake8 mcp_manager.py
	mypy mcp_manager.py

format:
	black mcp_manager.py tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python setup.py sdist bdist_wheel

upload: build
	twine upload dist/*