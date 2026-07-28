"""Guards G-3 / G-12, acceptance A-4: no author-specific domain content in the generic engine."""

from __future__ import annotations

import re
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / "src" / "loopr"

_DOMAIN_NOUNS = (
    "shariah",
    "kaide",
    "mizan",
    "halal",
    "gcp",
    "vertex",
    "bigquery",
)


def test_no_domain_specific_nouns_in_engine() -> None:
    for path in SRC_ROOT.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for noun in _DOMAIN_NOUNS:
            assert not re.search(rf"\b{noun}\b", text), f"{path} contains domain-specific noun {noun!r}"
