"""Standalone validation entrypoint."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent))

from tests.validation.run_validation import run_validation, main

if __name__ == "__main__":
    main()
