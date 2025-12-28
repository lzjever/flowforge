.PHONY: help clean install dev-install test test-builtin docs html clean-docs

help:
	@echo "Available targets:"
	@echo "  install       - Install the package"
	@echo "  dev-install   - Install with development dependencies"
	@echo "  test          - Run tests"
	@echo "  test-builtin  - Run built-in routines tests"
	@echo "  docs          - Build documentation"
	@echo "  html          - Build HTML documentation"
	@echo "  clean         - Clean build artifacts"
	@echo "  clean-docs    - Clean documentation build"

install:
	pip install -e .

dev-install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-builtin:
	pytest flowforge/builtin_routines/ -v

docs:
	cd docs && make html

html:
	cd docs && make html

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

clean-docs:
	cd docs && make clean

