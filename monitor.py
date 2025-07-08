from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict

from config import CACHE_DIR, today_str

_MONITOR_FILE = CACHE_DIR / "api_calls.json"


class APICallMonitor:
    """Simple file-based monitor to count API calls per day."""

    def __init__(self, path: Path = _MONITOR_FILE):
        self.path = path
        self.data: Dict[str, Dict[str, int]] = self._load()

    def _load(self):
        if self.path.exists():
            try:
                return json.loads(self.path.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _save(self):
        self.path.write_text(json.dumps(self.data))

    def increment(self, api_name: str):
        date_key = today_str()
        self.data.setdefault(date_key, {})
        self.data[date_key][api_name] = self.data[date_key].get(api_name, 0) + 1
        self._save()

    def get_count(self, api_name: str) -> int:
        date_key = today_str()
        return self.data.get(date_key, {}).get(api_name, 0)

    def reset(self):
        """Reset counts for current day."""
        date_key = today_str()
        self.data[date_key] = {}
        self._save()