#!/usr/bin/env python
"""Direct entry point for uvx execution."""

import sys
import os

# Add api/src to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'api', 'src'))

# Import and run the launcher
from kokoro_fastapi.launcher import main

if __name__ == "__main__":
    main()