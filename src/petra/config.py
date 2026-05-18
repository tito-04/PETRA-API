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


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
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

DEVICE_ID_SWITCH = os.getenv("PETRA_DEVICE_ID_SWITCH", "switch")
DEVICE_ID_SERVER_A = os.getenv("PETRA_DEVICE_ID_SERVER_A", "exigence1")
DEVICE_ID_SERVER_B = os.getenv("PETRA_DEVICE_ID_SERVER_B", "exigence2")

if not DUMMY_SWITCH_IDS:
    DUMMY_SWITCH_IDS = [DEVICE_ID_SWITCH]
if not DUMMY_SERVER_IDS:
    DUMMY_SERVER_IDS = [DEVICE_ID_SERVER_A, DEVICE_ID_SERVER_B]

SERVER_A_IP = os.getenv("PETRA_SERVER_A_IP", "10.255.35.93")
SERVER_B_IP = os.getenv("PETRA_SERVER_B_IP", "10.255.35.59")

SWITCH_SNMP_HOST = os.getenv("PETRA_SWITCH_SNMP_HOST", "10.255.35.8")
SWITCH_SNMP_VERSION = os.getenv("PETRA_SWITCH_SNMP_VERSION", "1")
SWITCH_SNMP_COMMUNITY = os.getenv("PETRA_SWITCH_SNMP_COMMUNITY", "it-atnog")
SWITCH_PORT_SERVER_A = _env_int("PETRA_SWITCH_PORT_SERVER_A", 13)
SWITCH_PORT_SERVER_B = _env_int("PETRA_SWITCH_PORT_SERVER_B", 14)
SWITCH_IFNAME_OID = os.getenv(
    "PETRA_SWITCH_IFNAME_OID",
    "1.3.6.1.2.1.31.1.1.1.1",
)
SWITCH_IFHCIN_OID = os.getenv(
    "PETRA_SWITCH_IFHCIN_OID",
    "1.3.6.1.2.1.31.1.1.1.6",
)
SWITCH_IFHCOUT_OID = os.getenv(
    "PETRA_SWITCH_IFHCOUT_OID",
    "1.3.6.1.2.1.31.1.1.1.10",
)

PDU_SNMP_HOST = os.getenv("PETRA_PDU_SNMP_HOST", "10.255.35.7")
PDU_SNMP_VERSION = os.getenv("PETRA_PDU_SNMP_VERSION", "2c")
PDU_SNMP_COMMUNITY = os.getenv("PETRA_PDU_SNMP_COMMUNITY", "it-atnog")
PDU_OUTLET_SWITCH = _env_int("PETRA_PDU_OUTLET_SWITCH", 9)
PDU_OUTLET_SERVER_A = _env_int("PETRA_PDU_OUTLET_SERVER_A", 24)
PDU_OUTLET_SERVER_B = _env_int("PETRA_PDU_OUTLET_SERVER_B", 20)
PDU_POWER_OID_BASE = os.getenv(
    "PETRA_PDU_POWER_OID_BASE",
    "1.3.6.1.4.1.534.6.6.7.6.5.1.3.0",
)

SNMP_TIMEOUT_SECONDS = _env_float("PETRA_SNMP_TIMEOUT_SECONDS", 2.0)
SNMP_RETRIES = _env_int("PETRA_SNMP_RETRIES", 1)
LIVE_ACCURACY = os.getenv(
    "PETRA_LIVE_ACCURACY",
    "ietf-power-and-energy:accuracy-measured-bronze",
)
