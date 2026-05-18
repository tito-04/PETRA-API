"""SNMP adapter placeholder for future integration."""

from __future__ import annotations


def get_switch_readings() -> dict:
    """
    Placeholder for SNMP-based readings.

    Expected return schema:
      {
        "instantaneous_power": float,
        "accuracy": "ietf-power-and-energy:accuracy-measured-...",
        "tx_gbps": float,
        "rx_gbps": float,
      }
    """
    raise NotImplementedError("SNMP adapter not implemented yet")
