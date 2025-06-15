# Building and Testing Kokoro-FastAPI

This guide covers how to build, test, and package Kokoro-FastAPI for distribution.

## Prerequisites

1. **Python 3.10+**
2. **uv** (recommended) or pip
3. **System dependencies** (optional but recommended):
   - espeak-ng: For phonemization
   - ffmpeg: For audio format conversion

## Quick Start

```bash
# Install development dependencies
make install-dev

# Check system dependencies
make deps-check

# Download models (optional, server will prompt on first run)
make models-download

# Run tests
make test

# Start the server
make run
```

**Note**: The package must be installed (`make install` or `make install-dev`) before running tests or using the CLI commands.

## Development Setup

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/mbailey/Kokoro-FastAPI.git
cd Kokoro-FastAPI

# Install with development dependencies
uv pip install -e ".[dev,test]"
# or
pip install -e ".[dev,test]"
```

### 2. Install System Dependencies

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install espeak-ng ffmpeg
```

**macOS:**
```bash
brew install espeak-ng ffmpeg
```

**Windows:**
- Download espeak-ng from [GitHub releases](https://github.com/espeak-ng/espeak-ng/releases)
- Download ffmpeg from [ffmpeg.org](https://ffmpeg.org/download.html)

### 3. Download Models

```bash
# Using the CLI tool
kokoro-models download --output ~/models/kokoro

# Or using make
make models-download
```

## Building the Package

### Build Distribution Packages

```bash
# Clean previous builds
make clean

# Build wheel and source distribution
make build

# Files will be in dist/
ls dist/
# kokoro_fastapi-0.4.0-py3-none-any.whl
# kokoro_fastapi-0.4.0.tar.gz
```

### Build Requirements

```bash
pip install build twine
```

### Manual Build Process

```bash
# Build wheel and sdist
python -m build

# Check the built packages
twine check dist/*
```

## Testing

### Run All Tests

```bash
# Using make
make test

# Or manually
python -m pytest api/tests -v
```

### Test Categories

1. **Unit Tests**
   ```bash
   make test-unit
   # or
   pytest api/tests/unit -v
   ```

2. **Integration Tests**
   ```bash
   make test-integration
   # or
   pytest api/tests/integration -v
   ```

3. **Package Tests**
   ```bash
   make package-test
   ```

### Test Coverage

```bash
# Run tests with coverage
pytest --cov=api/src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Testing the Installed Package

```bash
# Test in isolated environment
make package-test

# Manual testing
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate
pip install dist/*.whl
kokoro-start --help
kokoro-models --help
deactivate
rm -rf test_env
```

## Code Quality

### Linting

```bash
# Run all linters
make lint

# Run specific linters
ruff check api/src
mypy api/src --ignore-missing-imports
```

### Formatting

```bash
# Format code
make format

# Or manually
black api/src
ruff check api/src --fix
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## Testing Different Configurations

### Test with GPU

```bash
# Install GPU dependencies
make install-gpu

# Run with GPU
kokoro-start --gpu
```

### Test with CPU Only

```bash
# Install CPU dependencies
make install-cpu

# Run with CPU
kokoro-start --cpu
```

### Test Different Python Versions

```bash
# Using uv
uv venv --python 3.10
source .venv/bin/activate
make install-dev test

# Test with Python 3.11
uv venv --python 3.11
source .venv/bin/activate
make install-dev test
```

## Integration Testing

### Test the API

```bash
# Start the server
make run

# In another terminal, test the API
curl -X POST http://localhost:8880/v1/audio/speech \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Hello, world!",
    "model": "kokoro",
    "voice": "af_bella"
  }' \
  --output test.mp3
```

### Test with Different Models Directories

```bash
# Test with custom model directory
kokoro-start --models-dir /path/to/models

# Test with environment variable
export KOKORO_MODELS_DIR=/path/to/models
kokoro-start
```

## Debugging

### Verbose Output

```bash
# Run with debug logging
LOGLEVEL=DEBUG kokoro-start

# Check dependency issues
kokoro-start --skip-checks --force
```

### Common Issues

1. **Import errors**: Ensure you're in the right virtual environment
2. **Model not found**: Check models directory with `kokoro-models list`
3. **System dependencies**: Run `make deps-check` to verify

## Package Distribution Testing

### Test PyPI Installation (when released)

```bash
# Test from TestPyPI (if uploaded there)
pip install -i https://test.pypi.org/simple/ kokoro-fastapi

# Test from PyPI (when released)
pip install kokoro-fastapi
```

### Test GitHub Installation

```bash
# Install from GitHub
pip install git+https://github.com/mbailey/Kokoro-FastAPI.git

# Or with uv
uv pip install git+https://github.com/mbailey/Kokoro-FastAPI.git

# Test with uvx
uvx --from git+https://github.com/mbailey/Kokoro-FastAPI kokoro-start --help
```

## Continuous Integration

### GitHub Actions Workflow

The project should have CI that:
1. Runs on multiple Python versions (3.10, 3.11, 3.12)
2. Tests on multiple platforms (Ubuntu, macOS, Windows)
3. Runs linting and tests
4. Builds packages
5. Optionally publishes to PyPI

### Local CI Simulation

```bash
# Run all CI checks locally
make ci-test
```

## Release Process

1. **Update version**
   ```bash
   make bump-version
   ```

2. **Run all tests**
   ```bash
   make ci-test
   ```

3. **Build packages**
   ```bash
   make build
   ```

4. **Test packages**
   ```bash
   make package-test
   ```

5. **Tag release**
   ```bash
   git tag v0.4.0
   git push origin v0.4.0
   ```

6. **Upload to PyPI** (when ready)
   ```bash
   twine upload dist/*
   ```

## Docker Testing

### Test Docker Build

```bash
# CPU version
make docker-build
make docker-run

# GPU version
make docker-gpu-build
make docker-gpu-run
```

### Compare Docker vs Package

Run both versions and ensure they produce identical results:

```bash
# Docker version
docker-compose -f docker/cpu/docker-compose.yml up

# Package version
kokoro-start --port 8881
```

Then test both endpoints to ensure compatibility.