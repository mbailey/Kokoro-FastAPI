# Technical Specification: Python Package Distribution for Kokoro-FastAPI

## 1. Overview

This specification defines the technical requirements and implementation details for distributing Kokoro-FastAPI as a Python package while maintaining compatibility with the existing Docker-based deployment.

## 2. Package Metadata

### 2.1 PyPI Package Information
```toml
[project]
name = "kokoro-fastapi"
version = "0.4.0"  # Increment for package release
description = "FastAPI-based TTS server for Kokoro 82M model with OpenAI-compatible API"
readme = "README.md"
authors = [
    {name = "Original Author", email = "author@example.com"},
]
maintainers = [
    {name = "Package Maintainer", email = "maintainer@example.com"},
]
license = {text = "Apache-2.0"}  # Verify actual license
keywords = ["tts", "text-to-speech", "kokoro", "fastapi", "ai", "ml"]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "Topic :: Scientific/Engineering :: Artificial Intelligence",
    "License :: OSI Approved :: Apache Software License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.10"
```

### 2.2 Entry Points
```toml
[project.scripts]
kokoro-start = "kokoro_fastapi.launcher:main"
kokoro-models = "kokoro_fastapi.cli.models:main"
kokoro-config = "kokoro_fastapi.cli.config:main"
```

### 2.3 Optional Dependencies
```toml
[project.optional-dependencies]
gpu = ["torch>=2.0.0+cu118"]
cpu = ["torch>=2.0.0"]
dev = ["pytest", "pytest-asyncio", "httpx", "black", "ruff"]
notebook = ["ipython", "ipywidgets", "jupyter"]
all = ["kokoro-fastapi[gpu,notebook,dev]"]
```

## 3. File Structure

### 3.1 Package Layout
```
kokoro-fastapi/
├── api/
│   └── src/
│       ├── kokoro_fastapi/          # CLI and utilities
│       │   ├── __init__.py
│       │   ├── launcher.py          # Server launcher
│       │   ├── cli/
│       │   │   ├── __init__.py
│       │   │   ├── models.py       # Model management
│       │   │   └── config.py       # Configuration management
│       │   ├── utils/
│       │   │   ├── __init__.py
│       │   │   ├── deps.py         # System dependency checks
│       │   │   ├── download.py     # Model downloading
│       │   │   └── paths.py        # Path resolution
│       │   └── notebook/            # Jupyter support
│       │       ├── __init__.py
│       │       └── widgets.py
│       ├── core/                    # Core server code
│       ├── inference/               # Model inference
│       ├── routers/                 # API routes
│       └── services/                # Business logic
├── configs/                         # Default configurations
│   ├── default.yaml
│   └── examples/
├── docs/
├── tests/
└── pyproject.toml
```

### 3.2 Configuration Files

#### User Configuration Location
```python
# Priority order for configuration files:
# 1. Command line arguments
# 2. Environment variables
# 3. Config file specified via --config
# 4. ~/.config/kokoro/config.yaml (user)
# 5. /etc/kokoro/config.yaml (system)
# 6. {package}/configs/default.yaml (bundled)
```

#### Configuration Schema
```yaml
# config.yaml
version: 1
server:
  host: "0.0.0.0"
  port: 8880
  workers: 1
  log_level: "info"

models:
  dir: "~/models/kokoro"
  auto_download: true
  download_url: "https://huggingface.co/kokoro/v1_0"

voices:
  dir: "~/models/kokoro/voices"
  default: "af_bella"

inference:
  device: "auto"  # auto, cpu, cuda, mps
  use_gpu: true
  batch_size: 1
  compile_mode: "reduce-overhead"

audio:
  sample_rate: 24000
  format: "wav"

system:
  espeak_path: null  # Auto-detect
  ffmpeg_path: null  # Auto-detect
  cache_dir: "~/.cache/kokoro"
```

## 4. Core Components

### 4.1 Launcher Module
```python
# kokoro_fastapi/launcher.py
import argparse
import sys
from pathlib import Path
from typing import Optional

from .utils.deps import check_system_dependencies
from .utils.paths import resolve_paths
from .utils.config import load_config

def main():
    """Main entry point for kokoro-start command."""
    parser = create_parser()
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    config.update_from_args(args)
    
    # Check dependencies
    if not args.skip_checks:
        deps_ok = check_system_dependencies()
        if not deps_ok and not args.force:
            sys.exit(1)
    
    # Resolve paths
    paths = resolve_paths(config)
    
    # Check/download models
    if not paths.models_exist() and config.models.auto_download:
        from .cli.models import download_models
        download_models(paths.models_dir)
    
    # Start server
    start_server(config, paths)

def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Kokoro-FastAPI TTS Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kokoro-start                          # Start with defaults
  kokoro-start --models-dir ~/models    # Custom model directory
  kokoro-start --gpu --workers 4        # GPU with 4 workers
  kokoro-start --config custom.yaml     # Use config file
        """
    )
    
    # Server options
    parser.add_argument("--host", default=None, help="Host to bind to")
    parser.add_argument("--port", type=int, default=None, help="Port to bind to")
    parser.add_argument("--workers", type=int, default=None, help="Number of workers")
    
    # Model options
    parser.add_argument("--models-dir", help="Directory containing models")
    parser.add_argument("--voices-dir", help="Directory containing voices")
    parser.add_argument("--download", action="store_true", help="Download models if missing")
    
    # Device options
    parser.add_argument("--gpu", action="store_true", help="Use GPU if available")
    parser.add_argument("--cpu", action="store_true", help="Force CPU usage")
    parser.add_argument("--device", choices=["auto", "cpu", "cuda", "mps"], help="Device selection")
    
    # Other options
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--skip-checks", action="store_true", help="Skip system dependency checks")
    parser.add_argument("--force", action="store_true", help="Continue despite warnings")
    parser.add_argument("--version", action="version", version="%(prog)s 0.4.0")
    
    return parser

def start_server(config, paths):
    """Start the FastAPI server."""
    import os
    import uvicorn
    
    # Set environment variables
    env_vars = {
        "PROJECT_ROOT": str(paths.project_root),
        "MODEL_DIR": str(paths.models_dir),
        "VOICES_DIR": str(paths.voices_dir),
        "USE_GPU": str(config.inference.use_gpu).lower(),
        "DEVICE_TYPE": config.inference.device,
    }
    os.environ.update(env_vars)
    
    # Run uvicorn
    uvicorn.run(
        "main:app",
        host=config.server.host,
        port=config.server.port,
        workers=config.server.workers,
        log_level=config.server.log_level,
        app_dir=str(paths.api_src_dir),
    )
```

### 4.2 System Dependencies Checker
```python
# kokoro_fastapi/utils/deps.py
import shutil
import subprocess
import sys
from typing import Dict, List, Tuple

def check_system_dependencies() -> bool:
    """Check for required system dependencies."""
    deps = get_required_dependencies()
    missing = []
    warnings = []
    
    for name, spec in deps.items():
        result = check_dependency(name, spec)
        if result["status"] == "missing":
            missing.append((name, result))
        elif result["status"] == "warning":
            warnings.append((name, result))
    
    # Report results
    if missing or warnings:
        print_dependency_report(missing, warnings)
    
    return len(missing) == 0

def get_required_dependencies() -> Dict[str, Dict]:
    """Get required system dependencies."""
    return {
        "python": {
            "commands": [sys.executable, "--version"],
            "min_version": "3.10",
            "required": True,
        },
        "espeak-ng": {
            "commands": ["espeak-ng", "--version"],
            "fallback_commands": ["espeak", "--version"],
            "required": False,
            "feature": "phonemization",
            "install": {
                "Linux": "sudo apt-get install espeak-ng",
                "Darwin": "brew install espeak-ng",
                "Windows": "Download from https://github.com/espeak-ng/espeak-ng/releases",
            },
        },
        "ffmpeg": {
            "commands": ["ffmpeg", "-version"],
            "required": False,
            "feature": "audio format conversion",
            "install": {
                "Linux": "sudo apt-get install ffmpeg",
                "Darwin": "brew install ffmpeg",
                "Windows": "Download from https://ffmpeg.org/download.html",
            },
        },
    }

def check_dependency(name: str, spec: Dict) -> Dict:
    """Check a single dependency."""
    commands = spec.get("commands", [])
    if shutil.which(commands[0]):
        # Found, check version if needed
        if "min_version" in spec:
            version = get_version(commands)
            if not check_version(version, spec["min_version"]):
                return {
                    "status": "warning",
                    "message": f"{name} version {version} < {spec['min_version']}",
                }
        return {"status": "found"}
    
    # Try fallback commands
    for cmd in spec.get("fallback_commands", []):
        if shutil.which(cmd):
            return {
                "status": "warning", 
                "message": f"Found {cmd} instead of {commands[0]}",
            }
    
    return {
        "status": "missing" if spec["required"] else "warning",
        "feature": spec.get("feature"),
        "install": spec.get("install", {}),
    }
```

### 4.3 Model Management CLI
```python
# kokoro_fastapi/cli/models.py
import argparse
from pathlib import Path
from typing import Optional

from ..utils.download import ModelDownloader

def main():
    """Main entry point for kokoro-models command."""
    parser = create_parser()
    args = parser.parse_args()
    
    if args.command == "download":
        download_models(args.output, args.url, args.force)
    elif args.command == "list":
        list_models(args.dir)
    elif args.command == "verify":
        verify_models(args.dir)
    elif args.command == "clean":
        clean_models(args.dir, args.yes)

def create_parser():
    """Create argument parser for model management."""
    parser = argparse.ArgumentParser(description="Kokoro model management")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Download command
    download_parser = subparsers.add_parser("download", help="Download models")
    download_parser.add_argument("--output", "-o", default="~/models/kokoro",
                                help="Output directory")
    download_parser.add_argument("--url", help="Custom download URL")
    download_parser.add_argument("--force", action="store_true",
                                help="Force redownload")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List installed models")
    list_parser.add_argument("--dir", default="~/models/kokoro",
                            help="Models directory")
    
    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify model integrity")
    verify_parser.add_argument("--dir", default="~/models/kokoro",
                              help="Models directory")
    
    # Clean command
    clean_parser = subparsers.add_parser("clean", help="Remove old models")
    clean_parser.add_argument("--dir", default="~/models/kokoro",
                             help="Models directory")
    clean_parser.add_argument("--yes", "-y", action="store_true",
                             help="Skip confirmation")
    
    return parser

def download_models(output: str, url: Optional[str], force: bool):
    """Download Kokoro models."""
    output_path = Path(output).expanduser().absolute()
    downloader = ModelDownloader()
    
    print(f"Downloading models to {output_path}")
    success = downloader.download(
        output_path,
        url=url,
        force=force,
        progress=True,
    )
    
    if success:
        print("✓ Models downloaded successfully")
    else:
        print("✗ Failed to download models")
        sys.exit(1)
```

### 4.4 Path Resolution
```python
# kokoro_fastapi/utils/paths.py
import os
from pathlib import Path
from typing import Optional

class PathResolver:
    """Resolve paths for different installation methods."""
    
    def __init__(self, models_dir: Optional[str] = None):
        self.models_dir = self._resolve_models_dir(models_dir)
        self.project_root = self._find_project_root()
        self.api_src_dir = self._find_api_src_dir()
        
    def _resolve_models_dir(self, models_dir: Optional[str]) -> Path:
        """Resolve models directory from various sources."""
        # Priority: argument > env var > default
        if models_dir:
            return Path(models_dir).expanduser().absolute()
            
        env_dir = os.environ.get("KOKORO_MODELS_DIR")
        if env_dir:
            return Path(env_dir).expanduser().absolute()
            
        # Default locations
        default_locations = [
            Path.home() / "models" / "kokoro",
            Path("/opt/kokoro/models"),
            Path("./api/src/models"),
        ]
        
        # Return first existing or first default
        for loc in default_locations:
            if loc.exists():
                return loc.absolute()
                
        return default_locations[0].absolute()
    
    def _find_project_root(self) -> Path:
        """Find project root directory."""
        # Try various methods
        current = Path(__file__).parent
        
        # Look for marker files
        markers = ["pyproject.toml", "setup.py", ".git", "api"]
        while current != current.parent:
            if any((current / marker).exists() for marker in markers):
                return current
            current = current.parent
            
        # Fallback
        return Path.cwd()
    
    def _find_api_src_dir(self) -> Path:
        """Find the api/src directory."""
        candidates = [
            self.project_root / "api" / "src",
            Path(__file__).parent.parent,  # Relative to package
            Path.cwd() / "api" / "src",
        ]
        
        for candidate in candidates:
            if (candidate / "main.py").exists():
                return candidate
                
        raise RuntimeError("Could not find api/src directory")
    
    def models_exist(self) -> bool:
        """Check if models are installed."""
        required_files = [
            "v1_0/kokoro-v1_0.pth",
            "v1_0/config.json",
        ]
        return all((self.models_dir / f).exists() for f in required_files)
```

## 5. Integration Points

### 5.1 Environment Variable Mapping
```python
# Maps configuration to environment variables
CONFIG_TO_ENV = {
    "models.dir": "MODEL_DIR",
    "voices.dir": "VOICES_DIR", 
    "inference.use_gpu": "USE_GPU",
    "inference.device": "DEVICE_TYPE",
    "server.host": "HOST",
    "server.port": "PORT",
    "audio.sample_rate": "SAMPLE_RATE",
    "system.espeak_path": "PHONEMIZER_ESPEAK_PATH",
}
```

### 5.2 Backward Compatibility

All existing environment variables and Docker configurations remain functional:
- Docker paths (`/app/api/src/models`) work when detected
- Environment variables take precedence over config files
- Existing API endpoints unchanged
- Current directory structure preserved

## 6. Testing Strategy

### 6.1 Unit Tests
```python
# tests/test_package_mode.py
def test_path_resolution():
    """Test path resolution in package mode."""
    
def test_config_loading():
    """Test configuration file loading."""
    
def test_dependency_checking():
    """Test system dependency detection."""
```

### 6.2 Integration Tests
```python
# tests/test_cli_commands.py
def test_kokoro_start():
    """Test kokoro-start command."""
    
def test_model_download():
    """Test model downloading."""
```

### 6.3 Installation Tests
```bash
# Test various installation methods
pip install -e .
pip install git+https://github.com/user/repo
uvx --from git+https://github.com/user/repo kokoro-start
```

## 7. Documentation Updates

### 7.1 README.md Additions
```markdown
## Installation

### Docker (Recommended for Production)
[Existing Docker instructions]

### Python Package (Development & Integration)

#### Quick Start
```bash
# Run directly from GitHub
uvx --from git+https://github.com/org/kokoro-fastapi kokoro-start

# Or install as a tool
uv tool install git+https://github.com/org/kokoro-fastapi
kokoro-start --models-dir ~/models/kokoro
```

#### System Requirements
- Python 3.10+
- espeak-ng (recommended): Text phonemization
- ffmpeg (optional): Audio format conversion

#### First Run
The first time you run `kokoro-start`, it will:
1. Check system dependencies
2. Download models (~500MB) if needed
3. Start the FastAPI server on http://localhost:8880
```

### 7.2 Package Documentation
Create `docs/package-usage.md` with detailed instructions for:
- Installation methods
- Configuration options
- System dependency installation
- Troubleshooting guide
- API usage examples

## 8. Migration Path

### 8.1 For Docker Users
No changes required. Docker deployment continues to work exactly as before.

### 8.2 For New Users
1. Install Python 3.10+
2. Install system dependencies (optional)
3. Run `uvx --from git+... kokoro-start`
4. Follow prompts to download models
5. Access API at http://localhost:8880

### 8.3 For Developers
1. Clone repository
2. Install in development mode: `pip install -e .[dev]`
3. Run tests: `pytest`
4. Start server: `kokoro-start --config dev.yaml`

## 9. Performance Considerations

### 9.1 Startup Time
- First run: ~30s (dependency check + model verification)
- Subsequent runs: ~5s (skip checks with --skip-checks)
- Docker comparison: Similar after initial setup

### 9.2 Memory Usage
- Package mode: Direct Python process
- Docker mode: Additional container overhead (~100MB)
- Both modes: Same model memory requirements (~2GB)

### 9.3 Inference Performance
- Identical performance in both modes
- GPU acceleration works identically
- No overhead from packaging

## 10. Security Considerations

### 10.1 Model Downloads
- Verify checksums for downloaded models
- Use HTTPS for all downloads
- Allow custom download URLs for private models

### 10.2 Path Traversal
- Sanitize all user-provided paths
- Restrict model loading to specified directories
- No execution of downloaded content

### 10.3 Dependencies
- Pin all dependency versions
- Regular security updates
- Document known vulnerabilities

## 11. Future Enhancements

### 11.1 Phase 1 (Immediate)
- Basic package functionality
- CLI commands
- Model management

### 11.2 Phase 2 (3 months)
- Python API for programmatic use
- Jupyter notebook support
- Cloud function templates

### 11.3 Phase 3 (6 months)
- PyPI package release
- Conda package
- Plugin system for custom models

## 12. Conclusion

This specification provides a comprehensive plan for making Kokoro-FastAPI available as a Python package while maintaining full backward compatibility with the existing Docker-based deployment. The implementation is designed to be incremental, testable, and user-friendly.