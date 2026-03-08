from __future__ import annotations
from pathlib import Path

def read_text_file(path: str, max_bytes: int = 50_000) -> str:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return ""
    data = p.read_bytes()
    if len(data) > max_bytes:
        data = data[:max_bytes]
    try:
        return data.decode("utf-8", errors="replace")
    except Exception:
        return ""
