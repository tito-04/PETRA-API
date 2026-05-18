"""SNMP adapter for switch counters and PDU outlet power."""

from __future__ import annotations

import re
import subprocess
from typing import Iterable

from src.petra import config


class SnmpError(Exception):
    """Raised when an SNMP command fails or returns invalid data."""


_NUMBER_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _run_snmp_get(
    *,
    host: str,
    version: str,
    community: str,
    oid: str,
) -> str:
    cmd = [
        "snmpget",
        "-v",
        version,
        "-c",
        community,
        "-t",
        str(config.SNMP_TIMEOUT_SECONDS),
        "-r",
        str(config.SNMP_RETRIES),
        "-O",
        "qv",
        host,
        oid,
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
    )
    stdout = (result.stdout or "").strip()
    if result.returncode != 0 or not stdout:
        stderr = (result.stderr or "").strip()
        message = stderr or stdout or "SNMP command failed"
        raise SnmpError(message)
    return stdout


def _parse_number(value: str) -> float:
    match = _NUMBER_RE.search(value)
    if not match:
        raise SnmpError(f"Cannot parse numeric value from '{value}'")
    return float(match.group(0))


def get_pdu_power_watts(outlets: Iterable[int]) -> dict[int, float]:
    powers: dict[int, float] = {}
    for outlet in outlets:
        oid = f"{config.PDU_POWER_OID_BASE}.{outlet}"
        raw = _run_snmp_get(
            host=config.PDU_SNMP_HOST,
            version=config.PDU_SNMP_VERSION,
            community=config.PDU_SNMP_COMMUNITY,
            oid=oid,
        )
        powers[outlet] = _parse_number(raw)
    return powers


def get_switch_port_counters(ports: Iterable[int]) -> dict[int, dict[str, float]]:
    counters: dict[int, dict[str, float]] = {}
    for port in ports:
        rx_oid = f"{config.SWITCH_IFHCIN_OID}.{port}"
        tx_oid = f"{config.SWITCH_IFHCOUT_OID}.{port}"
        rx_raw = _run_snmp_get(
            host=config.SWITCH_SNMP_HOST,
            version=config.SWITCH_SNMP_VERSION,
            community=config.SWITCH_SNMP_COMMUNITY,
            oid=rx_oid,
        )
        tx_raw = _run_snmp_get(
            host=config.SWITCH_SNMP_HOST,
            version=config.SWITCH_SNMP_VERSION,
            community=config.SWITCH_SNMP_COMMUNITY,
            oid=tx_oid,
        )
        counters[port] = {
            "rx_bytes": _parse_number(rx_raw),
            "tx_bytes": _parse_number(tx_raw),
        }
    return counters


def get_switch_port_names(ports: Iterable[int]) -> dict[int, str]:
    names: dict[int, str] = {}
    for port in ports:
        oid = f"{config.SWITCH_IFNAME_OID}.{port}"
        raw = _run_snmp_get(
            host=config.SWITCH_SNMP_HOST,
            version=config.SWITCH_SNMP_VERSION,
            community=config.SWITCH_SNMP_COMMUNITY,
            oid=oid,
        )
        names[port] = raw
    return names
