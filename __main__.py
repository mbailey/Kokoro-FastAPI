#!/usr/bin/env python
"""Unified entry point for Kokoro-FastAPI that auto-detects system and GPU configuration."""

import os
import sys
import platform
import subprocess
import argparse
from pathlib import Path

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

def setup_environment(models_dir=None):
    """Set up environment variables based on OS and GPU type"""
    project_root = Path(__file__).parent.absolute()
    system = platform.system()
    gpu_type = detect_gpu()
    
    # Determine models directory
    if models_dir:
        models_path = Path(models_dir).expanduser().absolute()
    else:
        # Check environment variable
        env_models_dir = os.environ.get("KOKORO_MODELS_DIR")
        if env_models_dir:
            models_path = Path(env_models_dir).expanduser().absolute()
        else:
            # Default to current location
            models_path = project_root / "api" / "src" / "models"
    
    # Common environment variables
    env = {
        "PROJECT_ROOT": str(project_root),
        "PYTHONPATH": f"{project_root}:{project_root}/api",
        "MODEL_DIR": str(models_path),  # Directory containing models
        "VOICES_DIR": "src/voices/v1_0",
        "WEB_PLAYER_PATH": str(project_root / "web"),
        "USE_ONNX": "false",
    }
    
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
    
    return extras, gpu_type, models_path

def run_command(cmd, description=""):
    """Run a command and handle errors"""
    if description:
        print(f"\n{description}...")
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {description or 'Command'} failed with exit code {e.returncode}")
        sys.exit(1)

def main():
    """Main entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Kokoro-FastAPI Unified Launcher")
    parser.add_argument("--models-dir", "-m", 
                        help="Directory to store Kokoro models (default: api/src/models or $KOKORO_MODELS_DIR)")
    args = parser.parse_args()
    
    print("Kokoro-FastAPI Unified Launcher")
    print("=" * 40)
    
    # Detect system
    system = platform.system()
    print(f"Detected OS: {system}")
    
    # Setup environment and detect GPU
    extras, gpu_type, models_path = setup_environment(args.models_dir)
    print(f"Detected GPU: {gpu_type.upper()}")
    print(f"Installation mode: {extras.upper() if extras else 'BASE'}")
    print(f"Models directory: {models_path}")
    
    # Check if uv is available
    try:
        subprocess.run(["uv", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\nError: 'uv' is not installed. Please install it first:")
        print("  curl -LsSf https://astral.sh/uv/install.sh | sh")
        print("  or")
        print("  pip install uv")
        sys.exit(1)
    
    # Install dependencies
    if extras:
        run_command(f'uv pip install -e ".[{extras}]"', f"Installing {extras.upper()} dependencies")
    else:
        run_command('uv pip install -e .', "Installing base dependencies")
    
    # Download model
    model_version_path = models_path / "v1_0"
    if not model_version_path.exists() or not any(model_version_path.iterdir()):
        # Create directory if it doesn't exist
        model_version_path.mkdir(parents=True, exist_ok=True)
        run_command(
            f"uv run --no-sync python docker/scripts/download_model.py --output {model_version_path}",
            "Downloading Kokoro model"
        )
    else:
        print("\nModel already downloaded")
    
    # Warn about espeak on Unix-like systems
    if system in ["Linux", "Darwin"]:
        print("\nNote: espeak-ng should be installed system-wide for best results")
        print("  Ubuntu/Debian: sudo apt-get install espeak-ng")
        print("  macOS: brew install espeak-ng")
    
    # Start the server
    print(f"\nStarting Kokoro-FastAPI server on http://localhost:8880")
    print("Press Ctrl+C to stop")
    run_command("uv run --no-sync uvicorn api.src.main:app --host 0.0.0.0 --port 8880")

if __name__ == "__main__":
    main()