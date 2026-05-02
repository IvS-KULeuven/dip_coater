from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class NullSessionLog:
    """No-op session log used when session logging is disabled."""

    path: Path | None = None

    def write(self, event: str, **fields: Any) -> None:
        """Discard a session-log event.

        :param event: Event name that would have been written.
        :param fields: Structured event fields that would have been written.
        """
        return None


class SessionLog:
    """Append structured session events to a JSON-lines log file."""

    def __init__(self, path: str | Path) -> None:
        """Open a session-log destination.

        :param path: File path where JSON-line events should be appended.
        """
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, event: str, **fields: Any) -> None:
        """Write one structured session-log event.

        :param event: Event name to write.
        :param fields: JSON-serializable event fields.
        """
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
