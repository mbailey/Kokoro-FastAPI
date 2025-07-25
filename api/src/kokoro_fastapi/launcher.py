#!/usr/bin/env python
"""Unified entry point for Kokoro-FastAPI that auto-detects system and GPU configuration."""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple

try:
    # Try relative imports first (when run as module)
    from .utils.deps import check_system_dependencies
    from .utils.paths import PathResolver
    from .utils.download import download_models
except ImportError:
    # Fall back to absolute imports (when run as script)
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from kokoro_fastapi.utils.deps import check_system_dependencies
    from kokoro_fastapi.utils.paths import PathResolver
    from kokoro_fastapi.utils.download import download_models

def detect_gpu():
    """Detect GPU type: cuda, mps, or cpu"""
    # Try to import torch to check GPU availability
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        # Torch not installed yet, try system detection
        system = platform.system()
        if system in ["Linux", "Windows"]:
            # Check for NVIDIA GPU
            try:
                subprocess.run(["nvidia-smi"], capture_output=True, check=True)
                return "cuda"
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        elif system == "Darwin":
            # Check for Apple Silicon
            try:
                result = subprocess.run(["sysctl", "-n", "hw.optional.arm64"], 
                                      capture_output=True, text=True)
                if result.stdout.strip() == "1":
                    return "mps"
            except:
                pass
    return "cpu"

def setup_environment(paths: PathResolver) -> Tuple[str, str]:
    """Set up environment variables based on OS and GPU type.
    
    Args:
        paths: Path resolver instance
        
    Returns:
        Tuple of (extras, gpu_type)
    """
    system = platform.system()
    gpu_type = detect_gpu()
    
    # Get environment variables from path resolver
    env = paths.get_environment_vars()
    
    # Add system-agnostic settings
    env["USE_ONNX"] = "false"
    
    # GPU-specific settings
    if gpu_type == "cuda":
        env["USE_GPU"] = "true"
        extras = "gpu"
    elif gpu_type == "mps":
        env["USE_GPU"] = "true"
        env["DEVICE_TYPE"] = "mps"
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"  # Enable CPU fallback for unsupported MPS operations
        extras = ""  # Mac GPU uses base install
    else:
        env["USE_GPU"] = "false"
        extras = "cpu"
    
    # OS-specific settings
    if system == "Windows":
        env["PHONEMIZER_ESPEAK_LIBRARY"] = r"C:\Program Files\eSpeak NG\libespeak-ng.dll"
        env["PYTHONUTF8"] = "1"
    elif system == "Linux":
        env["ESPEAK_DATA_PATH"] = "/usr/lib/x86_64-linux-gnu/espeak-ng-data"
    
    # Apply environment variables
    os.environ.update(env)
    
    # Ensure PYTHONPATH includes the api/src directory
    current_pythonpath = os.environ.get("PYTHONPATH", "")
    if current_pythonpath:
        os.environ["PYTHONPATH"] = f"{env['PYTHONPATH']}:{current_pythonpath}"
    else:
        os.environ["PYTHONPATH"] = env['PYTHONPATH']
    
    return extras, gpu_type

def run_command(cmd, description="", cwd=None):
    """Run a command and handle errors"""
    if description:
        print(f"\n{description}...")
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error: {description or 'Command'} failed with exit code {e.returncode}")
        sys.exit(1)

def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Kokoro-FastAPI TTS Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kokoro-start                          # Start with defaults
  kokoro-start --models-dir ~/models    # Custom model directory
  kokoro-start --gpu --port 8080        # GPU with custom port
  kokoro-start --skip-checks            # Skip dependency checks
        """
    )
    
    # Path options
    parser.add_argument("--models-dir", "-m",
                        help="Directory containing models (default: ~/models/kokoro or $KOKORO_MODELS_DIR)")
    parser.add_argument("--voices-dir",
                        help="Directory containing voices (default: auto-detect)")
    
    # Server options
    parser.add_argument("--host", default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8880,
                        help="Port to bind to (default: 8880)")
    parser.add_argument("--workers", type=int, default=1,
                        help="Number of worker processes (default: 1)")
    
    # Device options
    parser.add_argument("--gpu", action="store_true",
                        help="Force GPU usage")
    parser.add_argument("--cpu", action="store_true",
                        help="Force CPU usage")
    
    # Other options
    parser.add_argument("--skip-checks", action="store_true",
                        help="Skip system dependency checks")
    parser.add_argument("--skip-install", action="store_true",
                        help="Skip package installation")
    parser.add_argument("--force", action="store_true",
                        help="Continue despite warnings")
    parser.add_argument("--download", action="store_true",
                        help="Force model download even if exists")
    parser.add_argument("--version", action="version",
                        version="%(prog)s 0.4.0")
    
    return parser


def is_uvx_environment():
    """Check if we're running in a uvx environment."""
    # Check for uvx-specific environment markers
    return (
        os.environ.get("UV_SCRIPT_PYTHON") is not None or
        'uvx' in sys.executable or
        '.cache/uv/scripts' in sys.executable
    )

def main():
    """Main entry point."""
    # Set MPS fallback early for macOS
    if platform.system() == "Darwin":
        os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
    
    parser = create_parser()
    args = parser.parse_args()
    
    # Auto-detect uvx and adjust behavior
    if is_uvx_environment():
        args.skip_install = True  # Can't install in uvx environment
        if not args.skip_checks:
            print("Note: Running in uvx environment, some features may be limited")
    
    # Also skip install if we're not in a git repository
    if not (Path.cwd() / ".git").exists() and not (Path.cwd() / "pyproject.toml").exists():
        args.skip_install = True
    
    print("Kokoro-FastAPI TTS Server")
    print("=" * 40)
    
    # Initialize path resolver
    paths = PathResolver(args.models_dir, args.voices_dir)
    
    # Check system dependencies
    if not args.skip_checks:
        print("\nChecking system dependencies...")
        deps_ok = check_system_dependencies(skip_optional=False)
        if not deps_ok and not args.force:
            print("\nSystem dependency check failed!")
            print("Use --skip-checks to skip or --force to continue anyway.")
            sys.exit(1)
    
    # Detect system and GPU
    system = platform.system()
    print(f"\nSystem Configuration:")
    print(f"  OS: {system}")
    
    # Setup environment
    extras, gpu_type = setup_environment(paths)
    
    # Handle GPU/CPU override
    if args.cpu:
        gpu_type = "cpu"
        extras = "cpu"
        os.environ["USE_GPU"] = "false"
    elif args.gpu and gpu_type == "cpu":
        print("  Warning: --gpu specified but no GPU detected")
    
    print(f"  GPU: {gpu_type.upper()}")
    print(f"  Models: {paths.models_dir}")
    print(f"  Voices: {paths.voices_dir}")
    
    # Check if uv is available (only if not skipping install)
    if not args.skip_install:
        # Check if we have a local project to install from
        pyproject_path = paths.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            print("\nSkipping dependency installation (not in project directory)")
            print("Assuming dependencies are already installed via uvx")
        else:
            try:
                subprocess.run(["uv", "--version"], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                print("\nError: 'uv' is not installed. Please install it first:")
                print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
                print("  or")
                print("  pip install uv")
                sys.exit(1)
            
            # Change to project root for installations
            os.chdir(paths.project_root)
            
            # Install dependencies
            print("\nInstalling dependencies...")
            if extras:
                run_command(f'uv pip install -e ".[{extras}]"', f"Installing {extras.upper()} dependencies")
            else:
                run_command('uv pip install -e .', "Installing base dependencies")
    
    # Check/download models
    if not paths.models_exist() or args.download:
        print("\nModel files not found.")
        response = input("Download Kokoro v1.0 models? (~500MB) [Y/n]: ")
        if response.lower() != 'n':
            success = download_models(
                paths.models_dir,
                version="v1_0",
                force=args.download
            )
            if not success:
                print("\nFailed to download models!")
                sys.exit(1)
        else:
            print("\nModels are required to run the server.")
            sys.exit(1)
    else:
        print("\n✓ Models found")
    
    # Start the server
    print(f"\nStarting Kokoro-FastAPI server on http://localhost:{args.port}")
    print("Press Ctrl+C to stop\n")
    
    # Set environment variables for the launcher
    os.environ["KOKORO_HOST"] = args.host
    os.environ["KOKORO_PORT"] = str(args.port)
    os.environ["KOKORO_WORKERS"] = str(args.workers)
    
    # Import uvicorn and run directly
    try:
        import uvicorn
        
        # When installed as a package via uvx, we should be able to import directly
        # UV handles the PYTHONPATH and package structure for us
        uvicorn.run(
            "kokoro_fastapi.main:app",
            host=args.host,
            port=args.port,
            workers=args.workers,
            reload=False,
            log_level="info"
        )
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"\nServer failed with error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()