"""Lightweight recent-activity log backed by a JSON file.

Keeps the dashboard's "recent activity" feed without introducing another
database dependency. Records are bounded (oldest dropped) and append-mostly,
guarded by a module-level lock for thread-safe access from FastAPI's sync
threadpool.
"""

import json
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger

ACTIVITY_FILE = Path(settings.DATA_DIR) / "activity.json"
MAX_RECORDS = 200

_lock = threading.Lock()


def record_activity(
    event_type: str,
    title: str,
    *,
    org_id: str | None = None,
    status: str = "success",
    detail: str = "",
    meta: dict[str, Any] | None = None,
) -> None:
    """Append an activity record, trimming to MAX_RECORDS."""
    try:
        with _lock:
            records = _read()
            records.append(
                {
                    "id": str(uuid.uuid4()),
                    "type": event_type,
                    "title": title,
                    "detail": detail,
                    "status": status,
                    "organization_id": org_id,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "meta": meta or {},
                }
            )
            records = records[-MAX_RECORDS:]
            ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
            ACTIVITY_FILE.write_text(
                json.dumps(records, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
    except Exception as e:
        logger.warning(f"Failed to record activity: {e}")


def recent_activity(
    org_id: str | None = None,
    limit: int = 50,
    event_type: str | None = None,
) -> list[dict[str, Any]]:
    """Return the most recent activity records (newest first)."""
    with _lock:
        records = _read()
    filtered = [r for r in records if r.get("organization_id") in (None, org_id)]
    if event_type:
        filtered = [r for r in filtered if r.get("type") == event_type]
    return list(reversed(filtered[-limit:]))


def _read() -> list[dict[str, Any]]:
    if not ACTIVITY_FILE.exists():
        return []
    try:
        data = json.loads(ACTIVITY_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:
        logger.warning(f"Failed to read activity file: {e}")
        return []
