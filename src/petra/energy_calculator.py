"""
Energy Calculator — aggregates per-device energy data into the PETRA
watts-per-gigabit metric and determines the least accurate data source.

Two calculation modes:

  calculate_from_live_data(device_readings, throughput_gbps)
    Primary mode — uses instantaneous_power values fetched live from each
    device on the path via RESTCONF.

    Formula per device i:
        wpg_i = instantaneous_power_i / throughput_gbps
    Total watts-per-gigabit = Σ wpg_i

  calculate(router_ids, throughput_gbps)
    Fallback mode — derives power from the topology model when the device
    server is unreachable.

    Formula per device i:
        load_i  = throughput / capacity_i
        power_i = baseline_i + (max_i - baseline_i) × load_i
        wpg_i   = power_i / throughput

In both modes the reported data-source-accuracy is the LEAST accurate
value among all contributing devices, as required by the PETRA YANG module.
"""

from src.mock.topology import ACCURACY_LEVELS, ROUTERS


def _accuracy_rank(accuracy: str) -> int:
    """Lower rank = less accurate (worse). Returns 0 for unknown values."""
    try:
        return ACCURACY_LEVELS.index(accuracy)
    except ValueError:
        return 0


def calculate_from_live_data(
    device_readings: list[dict],
    throughput_gbps: float,
) -> dict:
    """
    Compute aggregate PETRA energy metrics using **live** instantaneous_power
    values returned by each device on the path.

    Args:
        device_readings:  list of dicts, one per device on the path, each with:
                            - device_id           (str)
                            - instantaneous_power (float, Watts)
                            - accuracy            (str, identity string)
        throughput_gbps:  traffic throughput in Gb/s (from the PETRA query)

    Returns:
        {
            "watts_per_gigabit": float (3 decimal places),
            "data_source_accuracy": str  (least accurate identity string)
        }

    Raises:
        ValueError: if *throughput_gbps* is ≤ 0 or device_readings is empty.
    """
    if throughput_gbps <= 0:
        raise ValueError(f"throughput must be > 0, got {throughput_gbps}")
    if not device_readings:
        raise ValueError("device_readings must not be empty")

    total_wpg = 0.0
    worst_accuracy_rank = len(ACCURACY_LEVELS)
    worst_accuracy = ACCURACY_LEVELS[-1]

    for reading in device_readings:
        power_w = reading["instantaneous_power"]
        accuracy = reading["accuracy"]

        total_wpg += power_w / throughput_gbps

        rank = _accuracy_rank(accuracy)
        if rank < worst_accuracy_rank:
            worst_accuracy_rank = rank
            worst_accuracy = accuracy

    return {
        "watts_per_gigabit": round(total_wpg, 3),
        "data_source_accuracy": worst_accuracy,
    }


def calculate(
    router_ids: list[str],
    throughput_gbps: float,
) -> dict:
    """
    Compute aggregate PETRA energy metrics for *router_ids* at the given
    *throughput_gbps*.

    Each router's instantaneous power is modelled as:
        power = baseline + (max - baseline) × (throughput / capacity)

    Args:
        router_ids:      ordered list of router IDs on the path
        throughput_gbps: traffic throughput in Gb/s (from the PETRA query)

    Returns:
        {
            "watts_per_gigabit": float (3 decimal places),
            "data_source_accuracy": str  (least accurate identity string)
        }

    Raises:
        ValueError: if *throughput_gbps* is ≤ 0 or a router ID is unknown.
    """
    if throughput_gbps <= 0:
        raise ValueError(f"throughput must be > 0, got {throughput_gbps}")

    total_wpg = 0.0
    worst_accuracy_rank = len(ACCURACY_LEVELS)  # start at best, degrade
    worst_accuracy = ACCURACY_LEVELS[-1]

    for rid in router_ids:
        router = ROUTERS.get(rid)
        if router is None:
            raise ValueError(f"Unknown router ID: {rid}")

        baseline = router["baseline_power"]
        maximum = router["max_power"]
        capacity = router["capacity_gbps"]
        accuracy = router["accuracy"]

        load = min(throughput_gbps / capacity, 1.0)  # clamp to [0, 1]
        power_w = baseline + (maximum - baseline) * load
        total_wpg += power_w / throughput_gbps

        rank = _accuracy_rank(accuracy)
        if rank < worst_accuracy_rank:
            worst_accuracy_rank = rank
            worst_accuracy = accuracy

    return {
        "watts_per_gigabit": round(total_wpg, 3),
        "data_source_accuracy": worst_accuracy,
    }
