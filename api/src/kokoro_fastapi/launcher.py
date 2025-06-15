#!/usr/bin/env python
"""Unified entry point for Kokoro-FastAPI that auto-detects system and GPU configuration."""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path
from typing import Optional, Tuple

from .utils.deps import check_system_dependencies
from .utils.paths import PathResolver
from .utils.download import download_models

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
        env["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
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


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
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
    
    # Build uvicorn command
    cmd = [
        "uvicorn",
        "main:app",
        "--host", args.host,
        "--port", str(args.port),
        "--workers", str(args.workers),
    ]
    
    # Run from the api/src directory
    try:
        subprocess.run(cmd, cwd=paths.api_src_dir, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"\nServer failed with exit code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    main()