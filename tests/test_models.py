"""Unit tests for data models (Part A/B/C/D, Measurement, Stock)."""

import pytest

from src.models import Measurement, Part, PartA, PartB, PartC, PartD, Stock


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------

class TestMeasurement:
    def test_repr(self):
        m = Measurement(10, 20, 30)
        assert "10" in repr(m)
        assert "20" in repr(m)
        assert "30" in repr(m)

    def test_exact_compatibility(self):
        m1 = Measurement(10, 20, 30)
        m2 = Measurement(10, 20, 30)
        assert m1.is_compatible_with(m2)

    def test_incompatible_without_tolerance(self):
        m1 = Measurement(10, 20, 30)
        m2 = Measurement(10.5, 20, 30)
        assert not m1.is_compatible_with(m2, tolerance=0.0)

    def test_compatible_with_tolerance(self):
        m1 = Measurement(10, 20, 30)
        m2 = Measurement(10.4, 20, 30)
        assert m1.is_compatible_with(m2, tolerance=0.5)

    def test_incompatible_exceeds_tolerance(self):
        m1 = Measurement(10, 20, 30)
        m2 = Measurement(11, 20, 30)
        assert not m1.is_compatible_with(m2, tolerance=0.5)


# ---------------------------------------------------------------------------
# Part (base)
# ---------------------------------------------------------------------------

class TestPart:
    def _make_part(self, stock=5):
        return PartA(measurement=Measurement(10, 10, 10), stock=stock)

    def test_consume_reduces_stock(self):
        part = self._make_part(stock=5)
        part.consume(3)
        assert part.stock == 2

    def test_consume_all_stock(self):
        part = self._make_part(stock=5)
        part.consume(5)
        assert part.stock == 0

    def test_consume_raises_when_insufficient(self):
        part = self._make_part(stock=2)
        with pytest.raises(ValueError):
            part.consume(3)

    def test_replenish_increases_stock(self):
        part = self._make_part(stock=3)
        part.replenish(4)
        assert part.stock == 7

    def test_replenish_negative_raises(self):
        part = self._make_part(stock=3)
        with pytest.raises(ValueError):
            part.replenish(-1)


# ---------------------------------------------------------------------------
# PartA / PartB / PartC default names
# ---------------------------------------------------------------------------

class TestPartSubclasses:
    def test_part_a_default_name(self):
        p = PartA(measurement=Measurement(1, 1, 1))
        assert p.name == "Part A"

    def test_part_b_default_name(self):
        p = PartB(measurement=Measurement(1, 1, 1))
        assert p.name == "Part B"

    def test_part_c_default_name(self):
        p = PartC(measurement=Measurement(1, 1, 1))
        assert p.name == "Part C"


# ---------------------------------------------------------------------------
# Stock
# ---------------------------------------------------------------------------

class TestStock:
    def _make_stock(self):
        s = Stock()
        s.add_part_a(PartA(measurement=Measurement(10, 10, 10), stock=5))
        s.add_part_a(PartA(measurement=Measurement(20, 20, 20), stock=3))
        s.add_part_b(PartB(measurement=Measurement(10, 10, 10), stock=7))
        s.add_part_c(PartC(measurement=Measurement(10, 10, 10), stock=2))
        return s

    def test_total_stock_a(self):
        s = self._make_stock()
        assert s.total_stock_a() == 8

    def test_total_stock_b(self):
        s = self._make_stock()
        assert s.total_stock_b() == 7

    def test_total_stock_c(self):
        s = self._make_stock()
        assert s.total_stock_c() == 2

    def test_summary_keys(self):
        s = self._make_stock()
        summary = s.summary()
        assert set(summary.keys()) == {"Part A", "Part B", "Part C"}

    def test_summary_values(self):
        s = self._make_stock()
        summary = s.summary()
        assert summary["Part A"] == 8
        assert summary["Part B"] == 7
        assert summary["Part C"] == 2

    def test_empty_stock(self):
        s = Stock()
        assert s.total_stock_a() == 0
        assert s.total_stock_b() == 0
        assert s.total_stock_c() == 0
