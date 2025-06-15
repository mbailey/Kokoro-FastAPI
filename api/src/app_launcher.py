#!/usr/bin/env python
"""Direct app launcher that runs uvicorn programmatically."""

import sys
import os
from pathlib import Path

# Set up the Python path before any imports
api_src_dir = Path(__file__).parent
sys.path.insert(0, str(api_src_dir))
os.chdir(api_src_dir)

# Now we can import and run
import uvicorn

if __name__ == "__main__":
    # Import the app with proper path setup
    from main import app
    
    # Get host and port from environment or defaults
    host = os.environ.get("KOKORO_HOST", "0.0.0.0")
    port = int(os.environ.get("KOKORO_PORT", "8880"))
    workers = int(os.environ.get("KOKORO_WORKERS", "1"))
    
    # Run uvicorn directly
    if workers > 1:
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=workers,
            reload=False
        )
    else:
        # Single worker - can run the app object directly
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=False
        )