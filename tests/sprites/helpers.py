from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator


def parse(svg: str) -> ET.Element:
    return ET.fromstring(svg)


def local(tag: str) -> str:
    return tag.split("}")[-1]


def units(root: ET.Element) -> list[ET.Element]:
    """Every counted unit: an element whose class holds the token `u`."""
    return [e for e in root.iter() if "u" in e.attrib.get("class", "").split()]


def with_class(root: ET.Element, token: str) -> Iterator[ET.Element]:
    return (e for e in root.iter() if token in e.attrib.get("class", "").split())


def hexes(svg: str) -> set[str]:
    return {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", svg)}
