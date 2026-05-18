"""Smart plug adapter placeholder for future integration."""

from __future__ import annotations


def get_plug_reading() -> dict:
    """
    Placeholder for smart-plug readings.

    Expected return schema:
      {
        "instantaneous_power": float,
        "total_energy_wh": float | None,
      }
    """
    raise NotImplementedError("Smart plug adapter not implemented yet")
