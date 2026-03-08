from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict

STATE_PATH = Path(".gh_agent_state.json")

def load_state() -> Dict[str, Any]:
    if not STATE_PATH.exists():
        return {}
    return json.loads(STATE_PATH.read_text(encoding="utf-8"))

def save_state(state: Dict[str, Any]) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

def clear_state() -> None:
    if STATE_PATH.exists():
        STATE_PATH.unlink()
