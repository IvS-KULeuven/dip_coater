from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class NullSessionLog:
    path: Path | None = None

    def write(self, event: str, **fields: Any) -> None:
        return None


class SessionLog:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields: Any) -> None:
        payload = dict(fields)
        payload["timestamp"] = datetime.now(timezone.utc).isoformat()
        payload["event"] = event
        with self.path.open("a", encoding="utf-8") as log_file:
            log_file.write(
                json.dumps(payload, sort_keys=True, default=_json_default) + "\n"
            )


def _json_default(value: Any) -> str:
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)
