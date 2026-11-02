"""Where the pilot folder is, and whether this machine may offer Pilot as a data source."""

from __future__ import annotations

import datetime as dt
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator

from engine.forms import PILOT_FORMS
from engine.model import Form, Item, ItemType

ROOT = Path(__file__).resolve().parents[2]
CLASS_RE = re.compile(r"^[A-Za-z0-9]{1,8}$")
BANNER = "Pilot data: real sheets, roll numbers only"
LABEL_AI = "Read by AI"
LABEL_FILE = "Read from pilot answer file"


def folder() -> Path:
    return Path(os.environ.get("PILOT_DEMO_DIR", str(ROOT / "data" / "pilot")))


class Consent(BaseModel):
    consent_confirmed: bool
    confirmed_by: str = Field(min_length=2)
    date: dt.date
    scope: str = Field(min_length=3)


class PilotClass(BaseModel):
    class_code: str
    strength: int = Field(ge=1, le=80)
    teacher_label: str = Field(pattern=r"^T\d{1,2}$")  # T1, T2: never a name
    test_date: dt.date
    dictation: dict[int, int] = Field(default_factory=dict)  # item no -> number said, if it differs
    no_sheet: list[int] = Field(default_factory=list)
    absent: list[int] = Field(default_factory=list)

    @field_validator("class_code")
    @classmethod
    def _code(cls, v: str) -> str:
        if not CLASS_RE.match(v):
            raise ValueError("class_code must be letters and digits only, up to 8")
        return v


class ExtraItem(BaseModel):
    """An item printed on the paper after the ten check items (the pilot paper had 15). It is read
    and kept in the answer file; the error finder and the 2-item rule use the ten check items."""

    n: int = Field(ge=11, le=40)
    type: str = Field(pattern="^(add_carry|sub_anchor|sub_borrow)$")
    a: int
    b: int


class PilotTest(BaseModel):
    extra_items: list[ExtraItem] = Field(default_factory=list)
    name: str = "Pilot pre-test"
    form: str = "A"
    kind: str = "pre"
    date: dt.date | None = None
    paper_version: str = "pilot-form-a"


class Manifest(BaseModel):
    consent: Consent
    test: PilotTest = PilotTest()
    classes: list[PilotClass] = Field(min_length=1)

    def klass(self, code: str) -> PilotClass | None:
        return next((c for c in self.classes if c.class_code == code), None)


def form_for(manifest_class: PilotClass, form_key: str = "A") -> Form:
    """The pilot form with this class's dictation numbers (the pilot used different ones per
    class). Every other item is the printed pilot form's."""
    base = PILOT_FORMS[form_key]
    items = tuple(
        Item(it.n, it.type, manifest_class.dictation.get(it.n, it.a), it.b)
        if it.type is ItemType.DICTATION
        else it
        for it in base.items
    )
    return Form(base.label, items)


def read_form_for(manifest_class: PilotClass, test: PilotTest, form_key: str = "A") -> Form:
    """Every box printed on the paper, in order: the ten check items, then the extra items."""
    base = form_for(manifest_class, form_key)
    extra = tuple(Item(e.n, ItemType(e.type), e.a, e.b) for e in test.extra_items)
    return Form(base.label, base.items + extra)


@dataclass(frozen=True)
class Status:
    enabled: bool
    show: bool  # offer the option (disabled, with the reason) rather than hide it
    reason: str


def load_manifest(path: Path | None = None) -> Manifest:
    p = path or folder() / "manifest.yaml"
    data: Any = yaml.safe_load(p.read_text(encoding="utf-8"))
    return Manifest.model_validate(data)


def status() -> Status:
    """Pilot is on only when PILOT_DEMO=1, the folder exists and the manifest carries consent."""
    if os.environ.get("PILOT_DEMO") != "1":
        return Status(False, False, "Pilot data is off on this machine (PILOT_DEMO is not 1).")
    root = folder()
    if not root.is_dir():
        return Status(False, False, "There is no pilot folder on this machine.")
    path = root / "manifest.yaml"
    if not path.is_file():
        return Status(False, True, "The pilot folder has no manifest.yaml yet.")
    try:
        m = load_manifest(path)
    except (ValidationError, yaml.YAMLError, OSError, ValueError):
        return Status(False, True, "manifest.yaml is not valid. Fix it and reload.")
    if not m.consent.consent_confirmed:
        return Status(False, True, "The consent note in manifest.yaml is not confirmed.")
    if not (root / "pilot_answers.json").is_file():
        return Status(False, True, "Run `python tasks.py pilot-ingest` to make the answer file.")
    return Status(True, True, "")
