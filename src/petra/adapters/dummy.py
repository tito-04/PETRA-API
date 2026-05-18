"""Dummy adapter that mimics real device readings."""

from __future__ import annotations

from typing import Iterable

from src.petra import config


def _power_for_device(device_id: str) -> float:
    if device_id in config.DUMMY_SWITCH_IDS:
        return config.DUMMY_SWITCH_POWER_W
    if device_id in config.DUMMY_SERVER_IDS:
        return config.DUMMY_SERVER_POWER_W
    return config.DUMMY_SWITCH_POWER_W


def build_dummy_snapshot(device_ids: Iterable[str], timestamp: float) -> dict:
    devices: dict[str, dict[str, object]] = {}
    for device_id in device_ids:
        devices[device_id] = {
            "instantaneous_power": _power_for_device(device_id),
            "accuracy": config.DUMMY_ACCURACY,
        }
    return {
        "timestamp": timestamp,
        "throughput_gbps": config.DUMMY_THROUGHPUT_GBPS,
        "devices": devices,
        "source": "dummy",
    }
