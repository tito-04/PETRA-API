"""
Legacy Test Device Server — simulates network routers exposing energy data
via a RESTCONF-like REST API on port 8002.

Endpoint:
  GET /restconf/data/ietf-power-and-energy:energy-objects/{device_id}

Response schema mirrors ietf-power-and-energy YANG module:
  energy-objects:
    energy-entry:
      - object-id
      - source-component-id
      - power:
          instantaneous-power  (varies randomly within realistic bounds)
          nameplate-power
          unit-multiplier
          data-source-accuracy
          measurement-local
      - energy:
          total-energy-consumed
          unit-multiplier
          data-source-accuracy
          measurement-local

Run standalone:
  python -m src.mock.device_server
"""

import random
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from src.mock.topology import ROUTERS

app = FastAPI(title="Legacy Test Device Server", version="1.0.0")

# Each router keeps a running total of energy consumed (Wh), incremented
# on every request to simulate a real cumulative counter.
_energy_totals: dict[str, float] = {rid: 0.0 for rid in ROUTERS}
_start_time = time.time()


def _instantaneous_power(router: dict) -> float:
    """
    Return a random instantaneous power value for *router* within
    [baseline_power, max_power]. Values drift realistically around a
    midpoint so consecutive calls give slightly different results.
    """
    lo = router["baseline_power"]
    hi = router["max_power"]
    # Normal distribution centred at 60% of range, std = 15% of range
    midpoint = lo + 0.6 * (hi - lo)
    sigma = 0.15 * (hi - lo)
    value = random.gauss(midpoint, sigma)
    return round(max(lo, min(hi, value)), 3)


@app.get(
    "/restconf/data/ietf-power-and-energy:energy-objects/{device_id}",
    summary="Get energy data for a device",
)
async def get_energy_objects(device_id: str) -> JSONResponse:
    """
    Return ietf-power-and-energy:energy-objects data for *device_id*.
    Raises 404 if the device is not in the topology.
    """
    router = ROUTERS.get(device_id)
    if router is None:
        raise HTTPException(status_code=404, detail=f"Device '{device_id}' not found")

    inst_power = _instantaneous_power(router)

    # Accumulate energy (Wh): power (W) × elapsed fraction of an hour
    elapsed_h = (time.time() - _start_time) / 3600.0
    _energy_totals[device_id] = int(round(inst_power * elapsed_h))

    payload = {
        "ietf-power-and-energy:energy-objects": {
            "energy-entry": [
                {
                    "object-id": device_id,
                    "source-component-id": f"{device_id}-chassis",
                    "power": {
                        # int32 as required by ietf-power-and-energy YANG
                        "instantaneous-power": int(round(inst_power)),
                        "nameplate-power": int(router["max_power"]),
                        "unit-multiplier": "ietf-power-and-energy:multiplier-units",
                        "data-source-accuracy": router["accuracy"],
                        "measurement-local": True,
                    },
                    "energy": {
                        # uint64 as required by ietf-power-and-energy YANG
                        "total-energy-consumed": _energy_totals[device_id],
                        "unit-multiplier": "ietf-power-and-energy:multiplier-units",
                        "data-source-accuracy": router["accuracy"],
                        "measurement-local": True,
                    },
                }
            ]
        }
    }
    return JSONResponse(content=payload)


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "devices": list(ROUTERS.keys())}


if __name__ == "__main__":
    uvicorn.run("src.mock.device_server:app", host="0.0.0.0", port=8002, reload=False)
