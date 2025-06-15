"""Wrapper for main.py that handles imports correctly for uvicorn."""

import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Import the app
from main import app

__all__ = ["app"]