"""Pre-write the answer to every suggested question, at deploy time (the last step of the index build).

The answers are built by code from the rubric rows and the role's help pages (answer.curated), so
they need no network and no model, and the same sources always give the same answers. They are
shown offline, labelled "pre-written from the docs".
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from services.assistant import answer
from services.assistant.index import INDEX_DIR
from services.assistant.scopes import scopes


def build_all(index_dir: Path = INDEX_DIR) -> dict[str, dict[str, Any]]:
    answer.reload()
    lib = answer.library(index_dir)
    out = {role: answer.build_curated(scope, lib) for role, scope in scopes().items()}
    (index_dir / "curated.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8"
    )
    answer.reload()
    return out
