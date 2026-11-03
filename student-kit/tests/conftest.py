import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Test another file with: TSPTW_ALGO=baselines/greedy.py pytest
ALGO = ROOT / os.environ.get("TSPTW_ALGO", "algorithm.py")
