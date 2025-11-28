from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repository root is on sys.path so absolute imports work when tests
# are run from different working directories or virtual environments.
ROOT = Path(__file__).resolve().parent.parent
root_str = str(ROOT)
if root_str not in sys.path:
    sys.path.insert(0, root_str)
