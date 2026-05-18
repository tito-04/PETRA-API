"""
Path Resolver — maps (src_ip, dst_ip) to an ordered list of router IDs.

Wraps topology.get_path() and converts topology-level errors into the
typed exceptions expected by the PETRA server.
"""

from src.mock.topology import get_path
from src.petra import config


class InvalidAddressError(Exception):
    """Raised when one or both IP addresses are not served by any router."""


def resolve(src_ip: str, dst_ip: str) -> list[str]:
    """
    Return the ordered list of router IDs on the path from *src_ip* to
    *dst_ip*.

    Raises:
        InvalidAddressError: if either IP is not in the topology.
    """
    real_map = {
        config.SERVER_A_IP: config.DEVICE_ID_SERVER_A,
        config.SERVER_B_IP: config.DEVICE_ID_SERVER_B,
    }
    if src_ip in real_map and dst_ip in real_map:
        if src_ip == dst_ip:
            return [real_map[src_ip]]
        return [
            real_map[src_ip],
            config.DEVICE_ID_SWITCH,
            real_map[dst_ip],
        ]

    try:
        return get_path(src_ip, dst_ip)
    except ValueError as exc:
        raise InvalidAddressError(str(exc)) from exc
