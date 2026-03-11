"""Tests for topology.py — graph structure, IP lookup, path finding."""

import pytest
import networkx as nx

from src.mock.topology import (
    GRAPH,
    ROUTERS,
    get_path,
    lookup_router_for_ip,
)


class TestTopologyStructure:
    def test_six_routers_defined(self):
        assert len(ROUTERS) == 6

    def test_all_router_ids_present(self):
        assert set(ROUTERS.keys()) == {"R1", "R2", "R3", "R4", "R5", "R6"}

    def test_graph_has_correct_nodes(self):
        assert set(GRAPH.nodes) == {"R1", "R2", "R3", "R4", "R5", "R6"}

    def test_graph_is_connected(self):
        assert nx.is_connected(GRAPH)

    def test_router_energy_attributes(self):
        for r in ROUTERS.values():
            assert r["baseline_power"] > 0
            assert r["max_power"] > r["baseline_power"]
            assert r["capacity_gbps"] > 0
            assert r["accuracy"].startswith("ietf-power-and-energy:")


class TestIpLookup:
    def test_known_ip_returns_correct_router(self):
        assert lookup_router_for_ip("10.0.1.1") == "R1"
        assert lookup_router_for_ip("10.0.3.100") == "R3"
        assert lookup_router_for_ip("10.0.6.254") == "R6"

    def test_unknown_ip_returns_none(self):
        assert lookup_router_for_ip("192.168.1.1") is None
        assert lookup_router_for_ip("8.8.8.8") is None

    def test_invalid_string_returns_none(self):
        assert lookup_router_for_ip("not-an-ip") is None

    def test_network_address_returns_router(self):
        # .0 is the network address but still "in" the prefix
        assert lookup_router_for_ip("10.0.2.0") == "R2"


class TestPathFinding:
    def test_adjacent_routers(self):
        path = get_path("10.0.2.1", "10.0.5.1")
        assert path == ["R2", "R5"]

    def test_same_prefix_returns_single_router(self):
        path = get_path("10.0.1.1", "10.0.1.50")
        assert path == ["R1"]

    def test_path_length_r1_to_r6(self):
        path = get_path("10.0.1.1", "10.0.6.1")
        # Shortest path R1→R2→R3→R6 or R1→R4→R5→R6, both length 4
        assert len(path) == 4
        assert path[0] == "R1"
        assert path[-1] == "R6"

    def test_unknown_src_raises_value_error(self):
        with pytest.raises(ValueError, match="source"):
            get_path("1.2.3.4", "10.0.1.1")

    def test_unknown_dst_raises_value_error(self):
        with pytest.raises(ValueError, match="destination"):
            get_path("10.0.1.1", "1.2.3.4")
