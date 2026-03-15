# Simple Makefile for use with a uv-based development environment
# The at (@) prefix tells make to suppress output from the command
# The hyphen (-) prefix tells make to ignore errors (e.g., if a directory doesn't exist)

.PHONY: install
install: ## Install the virtual environment with dependencies
	@echo "🚀 Creating uv Python virtual environment"
	@uv python install 3.14
	@uv sync --python=3.14
	@echo "🚀 Installing Git prek hooks locally"
	@uv run prek install -f

.PHONY: check
check: ## Run code quality tools.
	@echo "🚀 Checking lock file consistency with 'pyproject.toml'"
	@uv lock --locked
	@echo "🚀 Auto-formatting/Linting code and documentation: Running prek"
	@uv run prek run -a
	@echo "🚀 Static type checking: Running mypy"
	@uv run mypy

.PHONY: format
format: ## Perform ruff formatting
	@uv run ruff format

.PHONY: lint
lint: ## Perform ruff linting
	@uv run ruff check --fix

.PHONY: typecheck
typecheck: ## Perform type checking
	@uv run mypy

.PHONY: test
test: ## Test the code with pytest.
	@echo "🚀 Testing code: Running pytest"
	@uv run python -Xutf8 -m pytest --cov --cov-config=pyproject.toml --cov-report=xml tests

# TODO Add stuff for building Sphinx docs

.PHONY: build
build: clean-build ## Build wheel file
	@echo "🚀 Creating wheel file"
	@uv build

.PHONY: tag
tag: ## Add a Git tag and push it to origin with syntax: make tag TAG=tag_name
	@echo "🚀 Creating git tag: ${TAG}"
	@git tag -a ${TAG} -m ""
	@echo "🚀 Pushing tag to origin: ${TAG}"
	@git push origin ${TAG}

# Define variables for files/directories to clean
BUILD_DIRS = build dist *.egg-info
DOC_DIRS = build
MYPY_DIRS = .mypy_cache dmypy.json dmypy.sock
TEST_DIRS = .cache .pytest_cache htmlcov
TEST_FILES = .coverage coverage.xml

.PHONY: clean-build
clean-build: ## Clean build artifacts
	@echo "🚀 Removing build artifacts"
	@uv run python -c "import shutil; import os; [shutil.rmtree(d, ignore_errors=True) for d in '$(BUILD_DIRS)'.split() if os.path.isdir(d)]"

.PHONY: clean-docs
clean-docs: ## Clean documentation artifacts
	@echo "🚀 Removing documentation artifacts"
	@uv run python -c "import shutil; import os; [shutil.rmtree(d, ignore_errors=True) for d in '$(DOC_DIRS)'.split() if os.path.isdir(d)]"

.PHONY: clean-mypy
clean-mypy: ## Clean mypy artifacts
	@echo "🚀 Removing mypy artifacts"
	@uv run python -c "import shutil; import os; [shutil.rmtree(d, ignore_errors=True) for d in '$(MYPY_DIRS)'.split() if os.path.isdir(d)]"

.PHONY: clean-pycache
clean-pycache: ## Clean pycache artifacts
	@echo "🚀 Removing pycache artifacts"
	@-find . -type d -name "__pycache__" -exec rm -r {} +

.PHONY: clean-ruff
clean-ruff: ## Clean ruff artifacts
	@echo "🚀 Removing ruff artifacts"
	@uv run ruff clean

.PHONY: clean-test
clean-test: ## Clean test artifacts
	@echo "🚀 Removing test artifacts"
	@uv run python -c "import shutil; import os; [shutil.rmtree(d, ignore_errors=True) for d in '$(TEST_DIRS)'.split() if os.path.isdir(d)]"
	@uv run python -c "from pathlib import Path; [Path(f).unlink(missing_ok=True) for f in '$(TEST_FILES)'.split()]"

.PHONY: clean
clean: clean-build clean-docs clean-mypy clean-pycache clean-ruff clean-test ## Clean all artifacts
	@echo "🚀 Cleaned all artifacts"

.PHONY: help
help:
	@uv run python -c "import re; \
	[[print(f'\033[36m{m[0]:<20}\033[0m {m[1]}') for m in re.findall(r'^([a-zA-Z_-]+):.*?## (.*)$$', open(makefile).read(), re.M)] for makefile in ('$(MAKEFILE_LIST)').strip().split()]"

.DEFAULT_GOAL := help
