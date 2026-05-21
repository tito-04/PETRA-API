"""
Device Client — fetches ietf-power-and-energy data from the testbed
device endpoint for a single router.

Uses httpx async so the PETRA server can query all path devices
concurrently with asyncio.gather().
"""

import httpx

# Base URL of the device endpoint (override in tests via DEVICE_SERVER_URL)
DEVICE_SERVER_URL = "http://localhost:8002"

_RESTCONF_PATH = "/restconf/data/ietf-power-and-energy:energy-objects/{device_id}"


class DeviceClientError(Exception):
    """Raised when the device server returns an unexpected response."""


async def get_energy(
    device_id: str,
    *,
    base_url: str = DEVICE_SERVER_URL,
) -> dict:
    """
    Query the device endpoint for *device_id* and return a normalised
    dict with keys:
        instantaneous_power  (float, Watts)
        capacity_gbps        (float, Gbps)   — from topology, injected below
        accuracy             (str, identity string)

    Raises:
        DeviceClientError: on HTTP errors or missing fields.
    """
    url = base_url + _RESTCONF_PATH.format(device_id=device_id)
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            response = await client.get(url)
        except httpx.RequestError as exc:
            raise DeviceClientError(f"Cannot reach device server: {exc}") from exc

    if response.status_code == 404:
        raise DeviceClientError(f"Device '{device_id}' not found on device endpoint")
    if response.status_code != 200:
        raise DeviceClientError(
            f"Device server returned {response.status_code} for '{device_id}'"
        )

    try:
        data = response.json()
        entry = data["ietf-power-and-energy:energy-objects"]["energy-entry"][0]
        power = entry["power"]
        return {
            "instantaneous_power": float(power["instantaneous-power"]),
            "accuracy": power["data-source-accuracy"],
        }
    except (KeyError, IndexError, ValueError) as exc:
        raise DeviceClientError(
            f"Unexpected response format from device '{device_id}': {exc}"
        ) from exc
