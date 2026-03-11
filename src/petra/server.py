"""
PETRA Server — implements the Path Energy Traffic Ratio API (PETRA).

Endpoint (RESTCONF-style):
  POST /restconf/operations/energy/query

Request body (application/yang-data+json):
  {
    "input": {
      "src-ip":     "<IPv4 or IPv6 address>",
      "dst-ip":     "<IPv4 or IPv6 address>",
      "throughput": <decimal Gb/s>
    }
  }

Success response:
  {
    "output": {
      "success": {
        "watts-per-gigabit":    <decimal>,
        "data-source-accuracy": "<identity string>"
      }
    }
  }

Invalid-address response:
  {
    "output": {
      "invalid-address": {}
    }
  }

Run standalone:
  python -m src.petra.server
"""

import asyncio

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.petra.device_client import DeviceClientError, get_energy
from src.petra.energy_calculator import calculate, calculate_from_live_data
from src.petra.path_resolver import InvalidAddressError, resolve

app = FastAPI(title="PETRA — Path Energy Traffic Ratio API", version="0.3.0")


# ── Request / Response models ─────────────────────────────────────────────────

class QueryInput(BaseModel):
    src_ip: str = Field(..., alias="src-ip", json_schema_extra={"example": "10.0.1.1"})
    dst_ip: str = Field(..., alias="dst-ip", json_schema_extra={"example": "10.0.6.1"})
    throughput: float = Field(..., description="Traffic throughput in Gb/s", json_schema_extra={"example": 10.0})

    model_config = {"populate_by_name": True}

    @field_validator("throughput")
    @classmethod
    def throughput_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("throughput must be greater than 0")
        return v


class QueryRequest(BaseModel):
    input: QueryInput


# ── Endpoint ──────────────────────────────────────────────────────────────────

@app.post(
    "/restconf/operations/energy/query",
    summary="Query energy consumption for a path",
    response_class=JSONResponse,
)
async def energy_query(body: QueryRequest) -> JSONResponse:
    """
    PETRA query endpoint.  Accepts the YANG-data+json body defined in
    ietf-petra.yang and returns watts-per-gigabit for the resolved path.
    """
    src_ip = body.input.src_ip
    dst_ip = body.input.dst_ip
    throughput = body.input.throughput

    # ── Resolve path ─────────────────────────────────────────────────────────
    try:
        router_ids = resolve(src_ip, dst_ip)
    except InvalidAddressError:
        return JSONResponse(
            status_code=200,
            content={"output": {"invalid-address": {}}},
        )

    # ── Query each device on the path concurrently via RESTCONF ────────────────
    # Primary path: fetch live instantaneous_power from the mock device server
    # and use those values to compute watts-per-gigabit.
    # Fallback: if the device server is unreachable, derive power from the
    # topology model (baseline + load formula).
    try:
        energy_readings = await asyncio.gather(
            *[get_energy(rid) for rid in router_ids]
        )
        # Attach device_id to each reading for traceability
        device_readings = [
            {"device_id": rid, **reading}
            for rid, reading in zip(router_ids, energy_readings)
        ]
        result = calculate_from_live_data(device_readings, throughput)
        data_source = "live"
    except DeviceClientError:
        # Device server unreachable — fall back to topology model
        result = calculate(router_ids, throughput)
        data_source = "topology-model"

    # ── Calculate aggregate metric ────────────────────────────────────────────

    return JSONResponse(
        status_code=200,
        content={
            "output": {
                "success": {
                    "watts-per-gigabit": result["watts_per_gigabit"],
                    "data-source-accuracy": result["data_source_accuracy"],
                    "path": router_ids,        # extra: useful for debugging
                    "data-source": data_source, # live | topology-model
                }
            }
        },
    )


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "PETRA"}


if __name__ == "__main__":
    uvicorn.run("src.petra.server:app", host="0.0.0.0", port=8003, reload=False)
