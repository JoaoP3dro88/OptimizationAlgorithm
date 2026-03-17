"""Unit tests for ProductionOptimizer."""

import pytest

from src.models import Measurement, PartA, PartB, PartC, PartD, Stock
from src.optimizer import ProductionOptimizer, ProductionOrder, OptimizationResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MEAS_S = Measurement(100, 50, 20)   # "small" measurement
MEAS_L = Measurement(200, 80, 30)   # "large" measurement


def make_stock(stock_a=10, stock_b=10, stock_c=10, meas=MEAS_S) -> Stock:
    s = Stock()
    s.add_part_a(PartA(measurement=meas, stock=stock_a))
    s.add_part_b(PartB(measurement=meas, stock=stock_b))
    s.add_part_c(PartC(measurement=meas, stock=stock_c))
    return s


def make_order(qty=1, meas=MEAS_S) -> ProductionOrder:
    d = PartD(
        name="Part D",
        required_measurement_a=meas,
        required_measurement_b=meas,
        required_measurement_c=meas,
    )
    return ProductionOrder(part_d=d, quantity=qty)


# ---------------------------------------------------------------------------
# Feasible quantity
# ---------------------------------------------------------------------------

class TestFeasibleQuantity:
    def test_limited_by_minimum_stock(self):
        stock = make_stock(stock_a=5, stock_b=3, stock_c=8)
        optimizer = ProductionOptimizer(stock=stock)
        order = make_order(qty=10)
        assert optimizer._feasible_quantity(order) == 3  # min(5, 3, 8)

    def test_zero_when_no_compatible_parts(self):
        stock = make_stock(stock_a=10, stock_b=10, stock_c=10, meas=MEAS_L)
        optimizer = ProductionOptimizer(stock=stock)
        order = make_order(qty=5, meas=MEAS_S)  # requires MEAS_S, stock has MEAS_L
        assert optimizer._feasible_quantity(order) == 0

    def test_compatible_with_tolerance(self):
        stock = Stock()
        # Part A is slightly off but within tolerance
        stock.add_part_a(PartA(measurement=Measurement(100.3, 50, 20), stock=5))
        stock.add_part_b(PartB(measurement=MEAS_S, stock=5))
        stock.add_part_c(PartC(measurement=MEAS_S, stock=5))

        optimizer = ProductionOptimizer(stock=stock, tolerance=0.5)
        order = make_order(qty=5)
        assert optimizer._feasible_quantity(order) == 5


# ---------------------------------------------------------------------------
# optimize – basic scenarios
# ---------------------------------------------------------------------------

class TestOptimize:
    def test_all_orders_fulfilled(self):
        stock = make_stock(stock_a=10, stock_b=10, stock_c=10)
        optimizer = ProductionOptimizer(stock=stock)
        orders = [make_order(qty=3), make_order(qty=4)]
        result = optimizer.optimize(orders)
        assert result.total_produced == 7
        assert len(result.infeasible_orders) == 0

    def test_order_partially_fulfilled(self):
        stock = make_stock(stock_a=5, stock_b=5, stock_c=5)
        optimizer = ProductionOptimizer(stock=stock)
        orders = [make_order(qty=8)]
        result = optimizer.optimize(orders)
        # Only 5 can be made; the remaining 3 are infeasible
        assert result.total_produced == 5
        assert len(result.infeasible_orders) == 1
        assert result.infeasible_orders[0].quantity == 3

    def test_no_stock_all_infeasible(self):
        stock = make_stock(stock_a=0, stock_b=0, stock_c=0)
        optimizer = ProductionOptimizer(stock=stock)
        orders = [make_order(qty=5)]
        result = optimizer.optimize(orders)
        assert result.total_produced == 0
        assert len(result.infeasible_orders) == 1

    def test_stock_consumed_after_optimize(self):
        stock = make_stock(stock_a=10, stock_b=10, stock_c=10)
        optimizer = ProductionOptimizer(stock=stock)
        orders = [make_order(qty=6)]
        optimizer.optimize(orders)
        assert stock.total_stock_a() == 4
        assert stock.total_stock_b() == 4
        assert stock.total_stock_c() == 4

    def test_sorting_maximises_throughput(self):
        """
        Two orders: the second has more achievable units (larger compatible stock).
        The optimizer should prefer it first, yielding a higher total.
        """
        stock = Stock()
        # MEAS_S stock: 10 units each
        stock.add_part_a(PartA(measurement=MEAS_S, stock=10))
        stock.add_part_b(PartB(measurement=MEAS_S, stock=10))
        stock.add_part_c(PartC(measurement=MEAS_S, stock=10))

        # MEAS_L stock: 2 units each
        stock.add_part_a(PartA(measurement=MEAS_L, stock=2))
        stock.add_part_b(PartB(measurement=MEAS_L, stock=2))
        stock.add_part_c(PartC(measurement=MEAS_L, stock=2))

        order_large = make_order(qty=2, meas=MEAS_L)
        order_small = make_order(qty=10, meas=MEAS_S)

        optimizer = ProductionOptimizer(stock=stock)
        result = optimizer.optimize([order_large, order_small])

        assert result.total_produced == 12  # all orders fulfilled
        assert len(result.infeasible_orders) == 0

    def test_empty_orders_list(self):
        stock = make_stock()
        optimizer = ProductionOptimizer(stock=stock)
        result = optimizer.optimize([])
        assert result.total_produced == 0
        assert result.feasible_orders == []
        assert result.infeasible_orders == []


# ---------------------------------------------------------------------------
# OptimizationResult.summary
# ---------------------------------------------------------------------------

class TestOptimizationResultSummary:
    def test_summary_contains_total(self):
        stock = make_stock(stock_a=5, stock_b=5, stock_c=5)
        optimizer = ProductionOptimizer(stock=stock)
        result = optimizer.optimize([make_order(qty=3)])
        summary = result.summary()
        assert "3" in summary
        assert "Total" in summary

    def test_summary_lists_infeasible_when_present(self):
        stock = make_stock(stock_a=1, stock_b=1, stock_c=1)
        optimizer = ProductionOptimizer(stock=stock)
        result = optimizer.optimize([make_order(qty=5)])
        summary = result.summary()
        assert "Infeasible" in summary or "infeasible" in summary.lower()
