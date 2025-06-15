"""Tests for package installation and CLI functionality."""

import subprocess
import sys
from pathlib import Path

import pytest


def test_package_imports():
    """Test that the package can be imported."""
    import kokoro_fastapi
    from kokoro_fastapi.utils import deps, paths, download
    from kokoro_fastapi.cli import models
    
    # Verify modules are importable
    assert hasattr(deps, 'check_system_dependencies')
    assert hasattr(paths, 'PathResolver')
    assert hasattr(download, 'ModelDownloader')
    assert hasattr(models, 'main')


def test_cli_commands_exist():
    """Test that CLI commands are available."""
    # Test kokoro-start
    result = subprocess.run(
        [sys.executable, "-m", "kokoro_fastapi.launcher", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Kokoro-FastAPI TTS Server" in result.stdout
    
    # Test kokoro-models
    result = subprocess.run(
        [sys.executable, "-m", "kokoro_fastapi.cli.models", "--help"],
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "Kokoro model management" in result.stdout


def test_path_resolver():
    """Test PathResolver functionality."""
    from kokoro_fastapi.utils.paths import PathResolver
    
    # Test with default paths
    resolver = PathResolver()
    assert resolver.project_root.exists()
    assert resolver.api_src_dir.exists()
    assert isinstance(resolver.models_dir, Path)
    assert isinstance(resolver.voices_dir, Path)
    
    # Test with custom paths
    custom_models = "/tmp/test_models"
    resolver = PathResolver(models_dir=custom_models)
    assert str(resolver.models_dir) == "/tmp/test_models"
    
    # Test environment variables
    env_vars = resolver.get_environment_vars()
    assert "PROJECT_ROOT" in env_vars
    assert "MODEL_DIR" in env_vars
    assert "VOICES_DIR" in env_vars


def test_dependency_checker():
    """Test system dependency checker."""
    from kokoro_fastapi.utils.deps import check_system_dependencies, get_required_dependencies
    
    # Test that we can get dependencies
    deps = get_required_dependencies()
    assert "python" in deps
    assert "espeak-ng" in deps
    assert "ffmpeg" in deps
    
    # Test that check runs without error
    # We don't assert the result as it depends on system
    result = check_system_dependencies(skip_optional=True)
    assert isinstance(result, bool)


def test_model_downloader():
    """Test ModelDownloader functionality."""
    from kokoro_fastapi.utils.download import ModelDownloader
    
    downloader = ModelDownloader(progress=False)
    
    # Test available models
    models = downloader.list_available_models()
    assert "v1_0" in models
    
    # Test model info
    info = downloader.get_model_info("v1_0")
    assert info is not None
    assert "files" in info
    assert "url" in info


def test_config_flexibility():
    """Test that config works in package mode."""
    try:
        from core.config import Settings, get_default_model_dir, get_default_voices_dir
    except ImportError:
        # Skip if torch not installed
        pytest.skip("Torch not installed, skipping config test")
    
    # Test default functions
    model_dir = get_default_model_dir()
    voices_dir = get_default_voices_dir()
    assert isinstance(model_dir, str)
    assert isinstance(voices_dir, str)
    
    # Test settings creation
    settings = Settings()
    assert hasattr(settings, 'model_dir')
    assert hasattr(settings, 'voices_dir')


def test_launcher_argument_parsing():
    """Test launcher argument parsing."""
    from kokoro_fastapi.launcher import create_parser
    
    parser = create_parser()
    
    # Test default arguments
    args = parser.parse_args([])
    assert args.host == "0.0.0.0"
    assert args.port == 8880
    assert args.workers == 1
    assert not args.skip_checks
    
    # Test custom arguments
    args = parser.parse_args([
        "--models-dir", "/custom/models",
        "--port", "9000",
        "--gpu",
        "--skip-checks"
    ])
    assert args.models_dir == "/custom/models"
    assert args.port == 9000
    assert args.gpu
    assert args.skip_checks


def test_models_cli_parsing():
    """Test models CLI argument parsing."""
    from kokoro_fastapi.cli.models import create_parser
    
    parser = create_parser()
    
    # Test download command
    args = parser.parse_args(["download", "--output", "/tmp/models"])
    assert args.command == "download"
    assert args.output == "/tmp/models"
    
    # Test list command
    args = parser.parse_args(["list", "--dir", "/tmp/models"])
    assert args.command == "list"
    assert args.dir == "/tmp/models"
    
    # Test info command
    args = parser.parse_args(["info", "v1_0"])
    assert args.command == "info"
    assert args.version == "v1_0"


@pytest.mark.skipif(
    not Path("/usr/bin/espeak-ng").exists() and not Path("/usr/local/bin/espeak-ng").exists(),
    reason="espeak-ng not installed"
)
def test_espeak_detection():
    """Test that espeak is properly detected when installed."""
    from kokoro_fastapi.utils.deps import check_dependency, get_required_dependencies
    
    deps = get_required_dependencies()
    espeak_spec = deps["espeak-ng"]
    
    result = check_dependency("espeak-ng", espeak_spec)
    assert result["status"] in ["found", "warning"]


def test_gpu_detection():
    """Test GPU detection logic."""
    from kokoro_fastapi.launcher import detect_gpu
    
    # This will return cuda, mps, or cpu depending on system
    gpu_type = detect_gpu()
    assert gpu_type in ["cuda", "mps", "cpu"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])