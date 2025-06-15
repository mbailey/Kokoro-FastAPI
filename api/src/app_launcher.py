#!/usr/bin/env python
"""Direct app launcher that runs uvicorn programmatically."""

import sys
import os
from pathlib import Path

# Find the project root (where pyproject.toml is)
current_file = Path(__file__).resolve()
api_src_dir = current_file.parent
api_dir = api_src_dir.parent
project_root = api_dir.parent

# Add project root to Python path so imports work
sys.path.insert(0, str(project_root))

# Change to project root directory
os.chdir(project_root)

# Now we can import and run
import uvicorn

if __name__ == "__main__":
    # Get host and port from environment or defaults
    host = os.environ.get("KOKORO_HOST", "0.0.0.0")
    port = int(os.environ.get("KOKORO_PORT", "8880"))
    workers = int(os.environ.get("KOKORO_WORKERS", "1"))
    
    # Run using the full module path like Docker does
    uvicorn.run(
        "api.src.main:app",
        host=host,
        port=port,
        workers=workers,
        reload=False
    )