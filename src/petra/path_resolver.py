"""
Path Resolver — maps (src_ip, dst_ip) to an ordered list of router IDs.

Wraps topology.get_path() and converts topology-level errors into the
typed exceptions expected by the PETRA server.
"""

from src.mock.topology import get_path


class InvalidAddressError(Exception):
    """Raised when one or both IP addresses are not served by any router."""


def resolve(src_ip: str, dst_ip: str) -> list[str]:
    """
    Return the ordered list of router IDs on the path from *src_ip* to
    *dst_ip*.

    Raises:
        InvalidAddressError: if either IP is not in the topology.
    """
    try:
        return get_path(src_ip, dst_ip)
    except ValueError as exc:
        raise InvalidAddressError(str(exc)) from exc
