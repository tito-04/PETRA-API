"""Configuration for PETRA runtime behavior."""

from __future__ import annotations

import os


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_csv(name: str) -> list[str]:
    value = os.getenv(name, "")
    items = [item.strip() for item in value.split(",")]
    return [item for item in items if item]


DUMMY_SWITCH_POWER_W = _env_float("PETRA_DUMMY_SWITCH_POWER_W", 180.0)
DUMMY_SERVER_POWER_W = _env_float("PETRA_DUMMY_SERVER_POWER_W", 80.0)
DUMMY_THROUGHPUT_GBPS = _env_float("PETRA_DUMMY_THROUGHPUT_GBPS", 1.0)
DUMMY_ACCURACY = os.getenv(
    "PETRA_DUMMY_ACCURACY",
    "ietf-power-and-energy:accuracy-measured-bronze",
)
DUMMY_SWITCH_IDS = _env_csv("PETRA_DUMMY_SWITCH_IDS")
DUMMY_SERVER_IDS = _env_csv("PETRA_DUMMY_SERVER_IDS")

SAMPLER_INTERVAL_SECONDS = _env_float("PETRA_SAMPLER_INTERVAL_SECONDS", 5.0)
CACHE_MAX_AGE_SECONDS = _env_float("PETRA_CACHE_MAX_AGE_SECONDS", 15.0)

ENABLE_SAMPLER = _env_bool("PETRA_ENABLE_SAMPLER", default=False)
