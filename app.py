#!/usr/bin/env python3
"""
HuggingFace Spaces entry point for Personal Expense Optimizer.
This serves the environment dashboard + OpenEnv API.
"""

import sys
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from backend.app import app

if __name__ == "__main__":
    # Run on 0.0.0.0:7860 for HF Spaces
    app.run(host="0.0.0.0", port=7860, debug=False)
