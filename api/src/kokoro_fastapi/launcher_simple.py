#!/usr/bin/env python
"""Simplified launcher for uvx usage - minimal dependencies and no installation."""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_torch():
    """Check if torch is available and give helpful error if not."""
    try:
        import torch
        return True
    except ImportError:
        print("Error: PyTorch is not installed.")
        print("\nTo use kokoro-start with uvx, you need to specify torch:")
        print('  uvx --with torch "kokoro-start"')
        print("\nOr install the package locally:")
        print("  pip install git+https://github.com/mbailey/Kokoro-FastAPI")
        return False

def simple_main():
    """Simplified main for uvx usage."""
    parser = argparse.ArgumentParser(
        description="Kokoro-FastAPI TTS Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument("--host", default="0.0.0.0",
                        help="Host to bind to (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8880,
                        help="Port to bind to (default: 8880)")
    parser.add_argument("--models-dir", "-m",
                        help="Directory containing models (default: ~/models/kokoro)")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip model download prompt")
    
    args = parser.parse_args()
    
    print("Kokoro-FastAPI TTS Server (uvx mode)")
    print("=" * 40)
    
    # Check torch
    if not check_torch():
        sys.exit(1)
    
    # Determine paths
    if args.models_dir:
        models_dir = Path(args.models_dir).expanduser().absolute()
    else:
        models_dir = Path.home() / "models" / "kokoro"
    
    models_dir.mkdir(parents=True, exist_ok=True)
    model_path = models_dir / "v1_0"
    
    # Set environment variables
    project_root = Path(__file__).parent.parent.parent.parent.parent
    api_src = project_root / "api" / "src"
    
    os.environ["PROJECT_ROOT"] = str(project_root)
    os.environ["PYTHONPATH"] = f"{project_root}:{api_src}"
    os.environ["MODEL_DIR"] = str(models_dir)
    os.environ["VOICES_DIR"] = str(api_src / "voices" / "v1_0")
    os.environ["WEB_PLAYER_PATH"] = str(project_root / "web")
    os.environ["USE_ONNX"] = "false"
    os.environ["USE_GPU"] = "false"  # Default to CPU for uvx
    
    print(f"Models directory: {models_dir}")
    
    # Check for models
    if not model_path.exists() or not any(model_path.iterdir() if model_path.exists() else []):
        if args.skip_download:
            print("\nError: Models not found. Use --models-dir or download them first.")
            sys.exit(1)
        
        print("\nModels not found. Downloading...")
        try:
            # Import here to avoid dependency issues
            from kokoro_fastapi.utils.download import download_models
            success = download_models(models_dir, version="v1_0")
            if not success:
                print("Failed to download models!")
                sys.exit(1)
        except ImportError:
            print("\nCannot download models automatically in uvx mode.")
            print("Please download manually or install the package locally.")
            sys.exit(1)
    else:
        print("✓ Models found")
    
    # Start server
    print(f"\nStarting server on http://localhost:{args.port}")
    print("Press Ctrl+C to stop\n")
    
    cmd = [
        sys.executable, "-m", "uvicorn",
        "main:app",
        "--host", args.host,
        "--port", str(args.port),
    ]
    
    try:
        # Change to api/src directory
        os.chdir(api_src)
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"\nServer failed with exit code {e.returncode}")
        sys.exit(1)

if __name__ == "__main__":
    simple_main()