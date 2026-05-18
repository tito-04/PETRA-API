"""
End-to-end tests for the PETRA API server (src/petra/server.py).

Uses FastAPI's TestClient (httpx) so no real HTTP server is needed.

Two test modes:
  - Fallback mode (default): device server not running → PETRA uses the
    topology model and reports data-source = "topology-model".
  - Live mode (mocked): device_client.get_energy is patched to return fake
    live readings → PETRA uses calculate_from_live_data and reports
    data-source = "live".
"""

import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.petra.server import app

client = TestClient(app)


class TestHealthEndpoint:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestMetricsEndpoint:
    def test_metrics_ok(self):
        r = client.get("/metrics")
        assert r.status_code == 200
        assert "petra_last_query_watts_per_gigabit" in r.text


class TestEnergyQueryCache:
    def _post(self, src_ip: str, dst_ip: str, throughput: float) -> dict:
        return client.post(
            "/restconf/operations/energy/query",
            json={"input": {"src-ip": src_ip, "dst-ip": dst_ip, "throughput": throughput}},
        )

    def test_cache_snapshot_used(self, monkeypatch):
        from src.mock.topology import ROUTERS
        from src.petra.adapters.dummy import build_dummy_snapshot
        from src.petra.cache import clear_snapshot, update_snapshot
        from src.petra import config

        snapshot = build_dummy_snapshot(list(ROUTERS.keys()), timestamp=time.time())
        asyncio.run(update_snapshot(snapshot))
        monkeypatch.setattr(config, "CACHE_MAX_AGE_SECONDS", 60.0)

        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        assert r.json()["output"]["success"]["data-source"] == "dummy"

        asyncio.run(clear_snapshot())


class TestEnergyQuery:
    def _post(self, src_ip: str, dst_ip: str, throughput: float) -> dict:
        return client.post(
            "/restconf/operations/energy/query",
            json={"input": {"src-ip": src_ip, "dst-ip": dst_ip, "throughput": throughput}},
        )

    def test_valid_query_returns_200(self):
        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        assert r.status_code == 200

    def test_valid_query_has_success_key(self):
        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        assert "success" in r.json()["output"]

    def test_watts_per_gigabit_present_and_positive(self):
        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        wpg = r.json()["output"]["success"]["watts-per-gigabit"]
        assert isinstance(wpg, float)
        assert wpg > 0

    def test_accuracy_present(self):
        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        acc = r.json()["output"]["success"]["data-source-accuracy"]
        assert "accuracy-measured" in acc

    def test_path_field_present(self):
        r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        path = r.json()["output"]["success"]["path"]
        assert isinstance(path, list)
        assert len(path) >= 2

    def test_same_subnet_single_hop(self):
        r = self._post("10.0.2.1", "10.0.2.99", 5.0)
        assert r.status_code == 200
        path = r.json()["output"]["success"]["path"]
        assert path == ["R2"]

    def test_adjacent_routers_two_hops(self):
        r = self._post("10.0.2.1", "10.0.5.1", 10.0)
        path = r.json()["output"]["success"]["path"]
        assert path == ["R2", "R5"]

    def test_unknown_src_ip_returns_invalid_address(self):
        r = self._post("192.168.1.1", "10.0.6.1", 10.0)
        assert r.status_code == 200
        assert "invalid-address" in r.json()["output"]

    def test_unknown_dst_ip_returns_invalid_address(self):
        r = self._post("10.0.1.1", "172.16.0.1", 10.0)
        assert r.status_code == 200
        assert "invalid-address" in r.json()["output"]

    def test_both_ips_unknown_returns_invalid_address(self):
        r = self._post("1.2.3.4", "5.6.7.8", 10.0)
        assert r.status_code == 200
        assert "invalid-address" in r.json()["output"]

    def test_higher_throughput_lower_wpg(self):
        low = self._post("10.0.1.1", "10.0.6.1", 1.0).json()["output"]["success"]
        high = self._post("10.0.1.1", "10.0.6.1", 100.0).json()["output"]["success"]
        assert high["watts-per-gigabit"] < low["watts-per-gigabit"]

    def test_fallback_reports_topology_model_source(self):
        """When device server is unreachable the response declares fallback mode."""
        from src.petra.device_client import DeviceClientError
        with patch("src.petra.server.get_energy", AsyncMock(side_effect=DeviceClientError("unreachable"))):
            r = self._post("10.0.1.1", "10.0.6.1", 10.0)
        assert r.json()["output"]["success"]["data-source"] == "topology-model"


class TestEnergyQueryLiveData:
    """
    Tests that exercise the primary live-data path by mocking get_energy()
    so a real device server is not required.
    """

    def _post(self, src_ip: str, dst_ip: str, throughput: float) -> dict:
        return client.post(
            "/restconf/operations/energy/query",
            json={"input": {"src-ip": src_ip, "dst-ip": dst_ip, "throughput": throughput}},
        )

    def _fake_get_energy(self, power: float, accuracy: str):
        """Return an AsyncMock that always yields the given power and accuracy."""
        return AsyncMock(return_value={
            "instantaneous_power": power,
            "accuracy": accuracy,
        })

    def test_live_path_uses_device_power(self):
        """
        With mocked device readings the watts-per-gigabit must equal
        sum(instantaneous_power_i) / throughput.
        Path R2→R5 has 2 devices. Mock each at 100 W. At 10 Gb/s → 20.0 W/Gb.
        """
        mock_reading = AsyncMock(return_value={
            "instantaneous_power": 100.0,
            "accuracy": "ietf-power-and-energy:accuracy-measured-gold",
        })
        with patch("src.petra.server.get_energy", mock_reading):
            r = self._post("10.0.2.1", "10.0.5.1", 10.0)

        body = r.json()["output"]["success"]
        assert body["data-source"] == "live"
        assert body["watts-per-gigabit"] == 20.0   # (100 + 100) / 10

    def test_live_path_uses_worst_accuracy(self):
        """Accuracy must be the worst returned by any device on the path."""
        # Path R1→R2→R3 has 3 devices. Give them gold, silver, bronze.
        accuracies = [
            "ietf-power-and-energy:accuracy-measured-gold",
            "ietf-power-and-energy:accuracy-measured-silver",
            "ietf-power-and-energy:accuracy-measured-bronze",
        ]
        call_count = 0

        async def side_effect(device_id, **kwargs):
            nonlocal call_count
            acc = accuracies[call_count % len(accuracies)]
            call_count += 1
            return {"instantaneous_power": 100.0, "accuracy": acc}

        with patch("src.petra.server.get_energy", side_effect=side_effect):
            r = self._post("10.0.1.1", "10.0.3.1", 10.0)

        body = r.json()["output"]["success"]
        assert body["data-source"] == "live"
        assert "bronze" in body["data-source-accuracy"]
