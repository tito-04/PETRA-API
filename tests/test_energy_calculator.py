"""Tests for energy_calculator.py."""

import pytest

from src.mock.topology import ACCURACY_LEVELS, ROUTERS
from src.petra.energy_calculator import calculate, calculate_from_live_data


class TestCalculate:
    def test_returns_required_keys(self):
        result = calculate(["R1"], throughput_gbps=10.0)
        assert "watts_per_gigabit" in result
        assert "data_source_accuracy" in result

    def test_watts_per_gigabit_positive(self):
        result = calculate(["R1", "R2", "R3"], throughput_gbps=10.0)
        assert result["watts_per_gigabit"] > 0

    def test_higher_throughput_lowers_wpg(self):
        """More traffic → devices more efficiently utilised → lower W/Gb."""
        low = calculate(["R1", "R2"], throughput_gbps=1.0)
        high = calculate(["R1", "R2"], throughput_gbps=50.0)
        assert high["watts_per_gigabit"] < low["watts_per_gigabit"]

    def test_more_hops_increases_wpg(self):
        short = calculate(["R1"], throughput_gbps=10.0)
        longer = calculate(["R1", "R2", "R3"], throughput_gbps=10.0)
        assert longer["watts_per_gigabit"] > short["watts_per_gigabit"]

    def test_accuracy_is_worst_among_path(self):
        """Result accuracy must be the least accurate in the path."""
        result = calculate(list(ROUTERS.keys()), throughput_gbps=10.0)
        accuracies = [ROUTERS[rid]["accuracy"] for rid in ROUTERS]
        worst_rank = min(ACCURACY_LEVELS.index(a) for a in accuracies)
        expected_worst = ACCURACY_LEVELS[worst_rank]
        assert result["data_source_accuracy"] == expected_worst

    def test_three_decimal_places(self):
        result = calculate(["R1", "R2"], throughput_gbps=10.0)
        # round() to 3 should produce same value
        assert result["watts_per_gigabit"] == round(result["watts_per_gigabit"], 3)

    def test_zero_throughput_raises(self):
        with pytest.raises(ValueError, match="throughput"):
            calculate(["R1"], throughput_gbps=0.0)

    def test_negative_throughput_raises(self):
        with pytest.raises(ValueError, match="throughput"):
            calculate(["R1"], throughput_gbps=-5.0)

    def test_unknown_router_raises(self):
        with pytest.raises(ValueError, match="Unknown router"):
            calculate(["R1", "R_UNKNOWN"], throughput_gbps=10.0)

    def test_throughput_above_capacity_clamped(self):
        """Throughput > capacity clamps load to 1.0 — should not raise."""
        r = ROUTERS["R3"]  # capacity ~50 Gbps
        result = calculate(["R3"], throughput_gbps=r["capacity_gbps"] * 10)
        assert result["watts_per_gigabit"] > 0


class TestCalculateFromLiveData:
    """Tests for calculate_from_live_data() — primary live-data path."""

    _READINGS = [
        {"device_id": "R1", "instantaneous_power": 200.0,
         "accuracy": "ietf-power-and-energy:accuracy-measured-gold"},
        {"device_id": "R2", "instantaneous_power": 150.0,
         "accuracy": "ietf-power-and-energy:accuracy-measured-silver"},
        {"device_id": "R3", "instantaneous_power": 100.0,
         "accuracy": "ietf-power-and-energy:accuracy-measured-bronze"},
    ]

    def test_returns_required_keys(self):
        result = calculate_from_live_data(self._READINGS, throughput_gbps=10.0)
        assert "watts_per_gigabit" in result
        assert "data_source_accuracy" in result

    def test_correct_wpg_formula(self):
        """wpg = sum(power_i / throughput)"""
        result = calculate_from_live_data(self._READINGS, throughput_gbps=10.0)
        expected = round((200.0 + 150.0 + 100.0) / 10.0, 3)
        assert result["watts_per_gigabit"] == expected

    def test_single_device(self):
        readings = [{"device_id": "R1", "instantaneous_power": 300.0,
                     "accuracy": "ietf-power-and-energy:accuracy-measured-gold"}]
        result = calculate_from_live_data(readings, throughput_gbps=10.0)
        assert result["watts_per_gigabit"] == 30.0

    def test_accuracy_is_worst_in_list(self):
        """Must return the least accurate (bronze < silver < gold)."""
        result = calculate_from_live_data(self._READINGS, throughput_gbps=10.0)
        assert result["data_source_accuracy"] == \
            "ietf-power-and-energy:accuracy-measured-bronze"

    def test_all_same_accuracy(self):
        readings = [
            {"device_id": "R1", "instantaneous_power": 100.0,
             "accuracy": "ietf-power-and-energy:accuracy-measured-gold"},
            {"device_id": "R2", "instantaneous_power": 100.0,
             "accuracy": "ietf-power-and-energy:accuracy-measured-gold"},
        ]
        result = calculate_from_live_data(readings, throughput_gbps=5.0)
        assert result["data_source_accuracy"] == \
            "ietf-power-and-energy:accuracy-measured-gold"

    def test_higher_throughput_lowers_wpg(self):
        low = calculate_from_live_data(self._READINGS, throughput_gbps=1.0)
        high = calculate_from_live_data(self._READINGS, throughput_gbps=100.0)
        assert high["watts_per_gigabit"] < low["watts_per_gigabit"]

    def test_three_decimal_places(self):
        result = calculate_from_live_data(self._READINGS, throughput_gbps=10.0)
        assert result["watts_per_gigabit"] == round(result["watts_per_gigabit"], 3)

    def test_zero_throughput_raises(self):
        with pytest.raises(ValueError, match="throughput"):
            calculate_from_live_data(self._READINGS, throughput_gbps=0.0)

    def test_empty_readings_raises(self):
        with pytest.raises(ValueError, match="empty"):
            calculate_from_live_data([], throughput_gbps=10.0)
