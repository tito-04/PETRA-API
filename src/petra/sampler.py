"""Background sampler that refreshes the PETRA snapshot cache."""

from __future__ import annotations

import asyncio
import time

from src.petra import config
from src.petra.adapters.dummy import build_dummy_snapshot
from src.petra.adapters.snmp import SnmpError, get_pdu_power_watts, get_switch_port_counters
from src.petra.cache import update_snapshot


async def run_sampler() -> None:
    device_ids = [
        config.DEVICE_ID_SERVER_A,
        config.DEVICE_ID_SWITCH,
        config.DEVICE_ID_SERVER_B,
    ]
    prev_counters: dict[int, dict[str, float]] | None = None
    prev_time: float | None = None
    while True:
        now = time.time()
        try:
            outlet_powers = get_pdu_power_watts(
                [
                    config.PDU_OUTLET_SWITCH,
                    config.PDU_OUTLET_SERVER_A,
                    config.PDU_OUTLET_SERVER_B,
                ]
            )
            port_counters = get_switch_port_counters(
                [
                    config.SWITCH_PORT_SERVER_A,
                    config.SWITCH_PORT_SERVER_B,
                ]
            )
            throughput_gbps = 0.0
            if prev_counters is not None and prev_time is not None:
                dt = max(now - prev_time, 0.001)
                for port, counters in port_counters.items():
                    prev = prev_counters.get(port)
                    if prev is None:
                        continue
                    rx_delta = counters["rx_bytes"] - prev["rx_bytes"]
                    tx_delta = counters["tx_bytes"] - prev["tx_bytes"]
                    if rx_delta < 0:
                        rx_delta = 0
                    if tx_delta < 0:
                        tx_delta = 0
                    throughput_gbps += ((rx_delta + tx_delta) * 8) / dt / 1_000_000_000

            prev_counters = port_counters
            prev_time = now

            snapshot = {
                "timestamp": now,
                "throughput_gbps": throughput_gbps,
                "devices": {
                    config.DEVICE_ID_SWITCH: {
                        "instantaneous_power": outlet_powers[config.PDU_OUTLET_SWITCH],
                        "accuracy": config.LIVE_ACCURACY,
                    },
                    config.DEVICE_ID_SERVER_A: {
                        "instantaneous_power": outlet_powers[config.PDU_OUTLET_SERVER_A],
                        "accuracy": config.LIVE_ACCURACY,
                    },
                    config.DEVICE_ID_SERVER_B: {
                        "instantaneous_power": outlet_powers[config.PDU_OUTLET_SERVER_B],
                        "accuracy": config.LIVE_ACCURACY,
                    },
                },
                "source": "live",
            }
        except SnmpError:
            snapshot = build_dummy_snapshot(device_ids=device_ids, timestamp=now)
        await update_snapshot(snapshot)
        await asyncio.sleep(config.SAMPLER_INTERVAL_SECONDS)
