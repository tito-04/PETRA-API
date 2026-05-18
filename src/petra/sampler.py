"""Background sampler that refreshes the PETRA snapshot cache."""

from __future__ import annotations

import asyncio
import time

from src.mock.topology import ROUTERS
from src.petra.adapters.dummy import build_dummy_snapshot
from src.petra.cache import update_snapshot
from src.petra.config import SAMPLER_INTERVAL_SECONDS


async def run_sampler() -> None:
    device_ids = list(ROUTERS.keys())
    while True:
        now = time.time()
        snapshot = build_dummy_snapshot(device_ids=device_ids, timestamp=now)
        await update_snapshot(snapshot)
        await asyncio.sleep(SAMPLER_INTERVAL_SECONDS)
