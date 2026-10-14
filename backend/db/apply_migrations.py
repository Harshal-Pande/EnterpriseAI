"""Compatibility wrapper. Delegates to backend/db/migrate.py.

Do not add a second migration implementation here.
"""

from __future__ import annotations

import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from migrate import main

if __name__ == "__main__":
    main()
