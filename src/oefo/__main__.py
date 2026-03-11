"""
Entry point for running OEFO as a module: python -m oefo
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
