"""Prometheus metrics for PETRA."""

from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Gauge, generate_latest

REGISTRY = CollectorRegistry()

_DEVICE_POWER_WATTS = Gauge(
    "petra_device_power_watts",
    "Instantaneous power per device in watts.",
    ["device_id", "source"],
    registry=REGISTRY,
)

_DEVICE_ACCURACY_INFO = Gauge(
    "petra_device_accuracy_info",
    "Accuracy identity for device readings (label only).",
    ["device_id", "accuracy"],
    registry=REGISTRY,
)

_LAST_QUERY_WPG = Gauge(
    "petra_last_query_watts_per_gigabit",
    "Watts-per-gigabit for the last PETRA query.",
    ["data_source"],
    registry=REGISTRY,
)

_LAST_QUERY_THROUGHPUT = Gauge(
    "petra_last_query_throughput_gbps",
    "Throughput for the last PETRA query in Gb/s.",
    registry=REGISTRY,
)

_LAST_QUERY_PATH_HOPS = Gauge(
    "petra_last_query_path_hops",
    "Hop count for the last PETRA query.",
    registry=REGISTRY,
)


def record_device_power(
    device_id: str,
    power_watts: float,
    accuracy: str,
    source: str,
) -> None:
    _DEVICE_POWER_WATTS.labels(device_id=device_id, source=source).set(power_watts)
    _DEVICE_ACCURACY_INFO.labels(device_id=device_id, accuracy=accuracy).set(1)


def record_query_result(
    watts_per_gigabit: float,
    throughput_gbps: float,
    path_hops: int,
    data_source: str,
) -> None:
    _LAST_QUERY_WPG.labels(data_source=data_source).set(watts_per_gigabit)
    _LAST_QUERY_THROUGHPUT.set(throughput_gbps)
    _LAST_QUERY_PATH_HOPS.set(path_hops)


def render_metrics() -> bytes:
    return generate_latest(REGISTRY)
