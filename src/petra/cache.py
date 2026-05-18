"""In-memory snapshot cache for PETRA sampler data."""

from __future__ import annotations

import asyncio
import time
from typing import Any

_SNAPSHOT: dict[str, Any] | None = None
_LOCK = asyncio.Lock()


async def update_snapshot(snapshot: dict[str, Any]) -> None:
    async with _LOCK:
        global _SNAPSHOT
        _SNAPSHOT = snapshot


async def get_snapshot(max_age_seconds: float) -> dict[str, Any] | None:
    async with _LOCK:
        if _SNAPSHOT is None:
            return None
        age = time.time() - _SNAPSHOT["timestamp"]
        if age > max_age_seconds:
            return None
        return {
            **_SNAPSHOT,
            "devices": dict(_SNAPSHOT["devices"]),
        }


async def clear_snapshot() -> None:
    async with _LOCK:
        global _SNAPSHOT
        _SNAPSHOT = None
