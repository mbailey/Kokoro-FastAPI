# Kokoro-FastAPI Makefile
# Provides convenient commands for development, testing, and package management

.PHONY: help install install-dev install-gpu install-cpu test test-unit test-integration lint format clean build run dev deps-check models-download package-test docker-build docker-run

# Default target
help:
	@echo "Kokoro-FastAPI Development Commands"
	@echo "=================================="
	@echo ""
	@echo "Installation:"
	@echo "  make install        Install package with auto-detected GPU support"
	@echo "  make install-dev    Install package with development dependencies"
	@echo "  make install-gpu    Force install with GPU support"
	@echo "  make install-cpu    Force install with CPU support only"
	@echo ""
	@echo "Development:"
	@echo "  make run           Run the server with default settings"
	@echo "  make dev           Run in development mode with auto-reload"
	@echo "  make test          Run all tests"
	@echo "  make lint          Run code linters"
	@echo "  make format        Format code with black"
	@echo "  make clean         Clean build artifacts and caches"
	@echo ""
	@echo "Package Management:"
	@echo "  make build         Build distribution packages"
	@echo "  make package-test  Test package installation"
	@echo "  make deps-check    Check system dependencies"
	@echo "  make models-download Download models to ~/models/kokoro"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run Docker container"

# Installation targets
install:
	uv pip install -e .

install-dev:
	uv pip install -e ".[dev,test]"

install-gpu:
	uv pip install -e ".[gpu]"

install-cpu:
	uv pip install -e ".[cpu]"

# Development targets
run:
	kokoro-start --skip-install

dev:
	kokoro-start --skip-install --workers 1 --host 127.0.0.1

# Testing targets
test: test-unit test-integration

test-unit:
	@echo "Running unit tests..."
	python -m pytest api/tests/unit -v

test-integration:
	@echo "Running integration tests..."
	python -m pytest api/tests/integration -v

test-package:
	@echo "Testing package functionality..."
	python -m pytest tests/test_package.py -v

# Code quality targets
lint:
	@echo "Running linters..."
	ruff check api/src
	mypy api/src --ignore-missing-imports || true

format:
	@echo "Formatting code..."
	black api/src
	ruff check api/src --fix

# Build targets
build: clean
	@echo "Building distribution packages..."
	python -m build
	@echo "Build complete. Check dist/ directory."

clean:
	@echo "Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf api/src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Package management targets
deps-check:
	@echo "Checking system dependencies..."
	@cd api/src && python -c "from kokoro_fastapi.utils.deps import check_system_dependencies; check_system_dependencies()"

models-download:
	@echo "Downloading models..."
	kokoro-models download --output ~/models/kokoro

models-verify:
	@echo "Verifying models..."
	kokoro-models verify --dir ~/models/kokoro

# Package testing
package-test: build
	@echo "Testing package installation..."
	@echo "Creating temporary virtual environment..."
	@python -m venv test_env
	@echo "Installing package..."
	@./test_env/bin/pip install dist/*.whl
	@echo "Testing commands..."
	@./test_env/bin/kokoro-start --help
	@./test_env/bin/kokoro-models --help
	@echo "Cleaning up..."
	@rm -rf test_env
	@echo "Package test complete!"

# Docker targets
docker-build:
	@echo "Building Docker image..."
	docker-compose -f docker/cpu/docker-compose.yml build

docker-run:
	@echo "Running Docker container..."
	docker-compose -f docker/cpu/docker-compose.yml up

docker-gpu-build:
	@echo "Building GPU Docker image..."
	docker-compose -f docker/gpu/docker-compose.yml build

docker-gpu-run:
	@echo "Running GPU Docker container..."
	docker-compose -f docker/gpu/docker-compose.yml up

# Development shortcuts
shell:
	@echo "Starting Python shell with package imported..."
	@python -c "import IPython; IPython.embed()" || python

server-test:
	@echo "Starting server in test mode..."
	kokoro-start --skip-install --skip-checks --port 8881

# Installation verification
verify-install:
	@echo "Verifying installation..."
	@python -c "import kokoro_fastapi; print('✓ Package imported successfully')"
	@which kokoro-start > /dev/null && echo "✓ kokoro-start command found" || echo "✗ kokoro-start command not found"
	@which kokoro-models > /dev/null && echo "✓ kokoro-models command found" || echo "✗ kokoro-models command not found"

# Quick start for new users
quickstart: install deps-check
	@echo ""
	@echo "Quick start complete! Now run:"
	@echo "  make models-download  # Download models"
	@echo "  make run             # Start the server"

# CI/CD targets
ci-test:
	@echo "Running CI tests..."
	make lint
	make test
	make build

# Version management
version:
	@grep version pyproject.toml | head -1 | cut -d'"' -f2

bump-version:
	@echo "Current version: $$(make version)"
	@echo "Enter new version: "
	@read VERSION; \
	sed -i "s/version = \".*\"/version = \"$$VERSION\"/" pyproject.toml; \
	echo "Updated to version $$VERSION"