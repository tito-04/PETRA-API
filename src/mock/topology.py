"""
Network topology for the PETRA mock environment.

Topology (grid of 6 routers):

    R1 (10.0.1.0/24) --- R2 (10.0.2.0/24) --- R3 (10.0.3.0/24)
    |                         |                         |
    R4 (10.0.4.0/24) --- R5 (10.0.5.0/24) --- R6 (10.0.6.0/24)

Each router has energy attributes generated with a fixed seed so results
are reproducible across runs. Attributes per router:
  - baseline_power (W): power consumed with zero traffic
  - max_power (W):      power consumed at full capacity
  - capacity_gbps:      forwarding capacity of the device
  - accuracy:           data-source-accuracy identity string
"""

import ipaddress
import random
import networkx as nx

# Fixed seed → same "random" energy characteristics every run
_RNG = random.Random(42)

# Accuracy levels ordered from worst (index 0) to best (index -1)
# Used to pick the least accurate value when aggregating across a path
ACCURACY_LEVELS = [
    "ietf-power-and-energy:accuracy-measured-bronze",
    "ietf-power-and-energy:accuracy-measured-silver",
    "ietf-power-and-energy:accuracy-measured-gold",
]


def _make_router(router_id: str, prefix: str) -> dict:
    baseline = round(_RNG.uniform(50, 200), 2)
    max_pw = round(_RNG.uniform(200, 500), 2)
    capacity = round(_RNG.uniform(40, 400), 2)
    accuracy = _RNG.choice(ACCURACY_LEVELS)
    return {
        "id": router_id,
        "prefix": ipaddress.ip_network(prefix),
        "baseline_power": baseline,   # Watts at zero load
        "max_power": max_pw,          # Watts at full capacity
        "capacity_gbps": capacity,    # Gbps
        "accuracy": accuracy,         # data-source-accuracy identity
    }


# ── Router definitions ────────────────────────────────────────────────────────
ROUTERS: dict[str, dict] = {
    r["id"]: r
    for r in [
        _make_router("R1", "10.0.1.0/24"),
        _make_router("R2", "10.0.2.0/24"),
        _make_router("R3", "10.0.3.0/24"),
        _make_router("R4", "10.0.4.0/24"),
        _make_router("R5", "10.0.5.0/24"),
        _make_router("R6", "10.0.6.0/24"),
    ]
}

# ── Graph ─────────────────────────────────────────────────────────────────────
GRAPH = nx.Graph()
GRAPH.add_nodes_from(ROUTERS.keys())
GRAPH.add_edges_from([
    ("R1", "R2"), ("R2", "R3"),
    ("R4", "R5"), ("R5", "R6"),
    ("R1", "R4"), ("R2", "R5"), ("R3", "R6"),
])


# ── Public helpers ─────────────────────────────────────────────────────────────

def lookup_router_for_ip(ip_str: str) -> str | None:
    """Return the router ID whose prefix contains *ip_str*, or None."""
    try:
        addr = ipaddress.ip_address(ip_str)
    except ValueError:
        return None
    for router in ROUTERS.values():
        if addr in router["prefix"]:
            return router["id"]
    return None


def get_path(src_ip: str, dst_ip: str) -> list[str]:
    """
    Return the list of router IDs on the shortest path between the
    routers that serve *src_ip* and *dst_ip*.

    Raises:
        ValueError: if either IP is not served by any router in the topology.
        nx.NetworkXNoPath: if the graph is disconnected (shouldn't happen).
    """
    src_router = lookup_router_for_ip(src_ip)
    dst_router = lookup_router_for_ip(dst_ip)

    if src_router is None:
        raise ValueError(f"No router found for source IP: {src_ip}")
    if dst_router is None:
        raise ValueError(f"No router found for destination IP: {dst_ip}")

    return nx.shortest_path(GRAPH, src_router, dst_router)
