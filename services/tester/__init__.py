"""Tester profiles and privacy-safe usage stats (TESTER_STATS=1, public demo only).

Opt-in, coarse data only. A row belongs to the signed-in user (the normalised nickname is the user id, decided
2026-11-03); there is no device id or device hash. See docs/build/reports/TESTER-STATS.md.
"""

from __future__ import annotations

import os


def tester_stats_enabled() -> bool:
    """On only where the deployment sets TESTER_STATS=1."""
    return os.environ.get("TESTER_STATS", "0") == "1"
