from __future__ import annotations

import re


_whitespace = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    cleaned = text.replace("\u00a0", " ")
    cleaned = _whitespace.sub(" ", cleaned).strip()
    return cleaned
