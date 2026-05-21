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
from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.petra import config
from src.petra.cache import get_snapshot
from src.petra.device_client import DeviceClientError, get_energy
from src.petra.energy_calculator import calculate, calculate_from_live_data
from src.petra.metrics import CONTENT_TYPE_LATEST, record_device_power, record_query_result, render_metrics
from src.petra.path_resolver import InvalidAddressError, resolve
from src.petra.sampler import run_sampler

app = FastAPI(title="PETRA — Path Energy Traffic Ratio API", version="0.3.0")

_sampler_task: asyncio.Task | None = None


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
    # Primary path: fetch live instantaneous_power from the SNMP/PDU sources
    # and use those values to compute watts-per-gigabit.
    # Fallback: if the device server is unreachable, derive power from the
    # topology model (baseline + load formula).
    device_readings: list[dict] = []
    snapshot = await get_snapshot(config.CACHE_MAX_AGE_SECONDS)
    if snapshot is not None:
        snapshot_devices = snapshot["devices"]
        for rid in router_ids:
            reading = snapshot_devices.get(rid)
            if reading is None:
                device_readings = []
                break
            device_readings.append({"device_id": rid, **reading})
        if device_readings:
            result = calculate_from_live_data(device_readings, throughput)
            data_source = snapshot.get("source", "dummy")
        else:
            snapshot = None

    if snapshot is None:
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

    if data_source in {"live", "dummy"} and device_readings:
        for reading in device_readings:
            record_device_power(
                device_id=reading["device_id"],
                power_watts=reading["instantaneous_power"],
                accuracy=reading["accuracy"],
                source=data_source,
            )

    record_query_result(
        watts_per_gigabit=result["watts_per_gigabit"],
        throughput_gbps=throughput,
        path_hops=len(router_ids),
        data_source=data_source,
    )

    return JSONResponse(
        status_code=200,
        content={
            "output": {
                "success": {
                    "watts-per-gigabit": result["watts_per_gigabit"],
                    "data-source-accuracy": result["data_source_accuracy"],
                    "path": router_ids,        # extra: useful for debugging
                    "data-source": data_source, # dummy | live | topology-model
                }
            }
        },
    )


@app.get("/health", summary="Health check")
async def health() -> dict:
    return {"status": "ok", "service": "PETRA"}


@app.on_event("startup")
async def start_sampler() -> None:
    if not config.ENABLE_SAMPLER:
        return
    global _sampler_task
    if _sampler_task is None:
        _sampler_task = asyncio.create_task(run_sampler())


@app.on_event("shutdown")
async def stop_sampler() -> None:
    global _sampler_task
    if _sampler_task is None:
        return
    _sampler_task.cancel()
    try:
        await _sampler_task
    except asyncio.CancelledError:
        pass
    _sampler_task = None


@app.get("/metrics", summary="Prometheus metrics")
async def metrics() -> Response:
    return Response(render_metrics(), media_type=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    uvicorn.run("src.petra.server:app", host="0.0.0.0", port=8003, reload=False)
