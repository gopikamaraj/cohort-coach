"""Device-based tester profiles and privacy-safe usage stats (TESTER_STATS=1, public demo only).

Opt-in, coarse data only; the raw device id never reaches the server (only a salted hash made on the
device). See docs/build/reports/TESTER-STATS.md.
"""

from __future__ import annotations

import os


def tester_stats_enabled() -> bool:
    """On only where the deployment sets TESTER_STATS=1."""
    return os.environ.get("TESTER_STATS", "0") == "1"
