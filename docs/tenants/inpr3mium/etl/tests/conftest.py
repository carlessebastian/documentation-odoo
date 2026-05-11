"""Pytest config: anade el dir padre (etl/) al sys.path."""
from __future__ import annotations

import sys
from pathlib import Path

ETL_DIR = Path(__file__).resolve().parent.parent
if str(ETL_DIR) not in sys.path:
    sys.path.insert(0, str(ETL_DIR))
