"""
Production sequence optimizer for Part D.

The optimizer inspects current stock levels of Parts A, B and C and
determines the best order in which a list of Part D orders should be
produced so as to maximise throughput (i.e. the number of Part D units
that can be assembled before stock runs out).
"""

from dataclasses import dataclass, field
from typing import List, Optional

from .models import Measurement, PartA, PartB, PartC, PartD, Stock


@dataclass
class ProductionOrder:
    """A single production request: assemble *quantity* units of *part_d*."""

    part_d: PartD
    quantity: int = 1

    def __repr__(self) -> str:
        return f"ProductionOrder(part_d={self.part_d.name!r}, quantity={self.quantity})"


@dataclass
class OptimizationResult:
    """Outcome produced by :class:`ProductionOptimizer`."""

    sequence: List[ProductionOrder] = field(default_factory=list)
    feasible_orders: List[ProductionOrder] = field(default_factory=list)
    infeasible_orders: List[ProductionOrder] = field(default_factory=list)
    total_produced: int = 0

    def summary(self) -> str:
        lines = [
            "=== Optimization Result ===",
            f"Total Part D units produced : {self.total_produced}",
            f"Feasible orders ({len(self.feasible_orders)}):",
        ]
        for order in self.feasible_orders:
            lines.append(f"  - {order.part_d.name}: {order.quantity} unit(s)")
        if self.infeasible_orders:
            lines.append(f"Infeasible orders ({len(self.infeasible_orders)}) - insufficient stock:")
            for order in self.infeasible_orders:
                lines.append(f"  - {order.part_d.name}: {order.quantity} unit(s) requested")
        return "\n".join(lines)


class ProductionOptimizer:
    """
    Finds the best production sequence for Part D given stock of A, B and C.

    Strategy
    --------
    1. For each pending production order, calculate how many units of Part D
       can be assembled from current stock (considering measurement compatibility
       and available quantities).
    2. Sort orders by *feasibility score* (highest first) so that the most
       achievable orders are attempted first — maximising total throughput.
    3. Simulate stock consumption and collect feasible / infeasible results.

    Parameters
    ----------
    stock : Stock
        Current inventory of component parts.
    tolerance : float
        Measurement tolerance (mm) used when matching component parts to the
        required measurements of each Part D variant.
    """

    def __init__(self, stock: Stock, tolerance: float = 0.0) -> None:
        self.stock = stock
        self.tolerance = tolerance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def optimize(self, orders: List[ProductionOrder]) -> OptimizationResult:
        """
        Return an :class:`OptimizationResult` with the optimal production
        sequence derived from *orders*.
        """
        scored = [
            (order, self._feasible_quantity(order))
            for order in orders
        ]
        # Sort descending by achievable quantity so we favour productive orders.
        scored.sort(key=lambda x: x[1], reverse=True)

        result = OptimizationResult(sequence=list(orders))
        for order, achievable in scored:
            to_produce = min(order.quantity, achievable)
            if to_produce > 0:
                self._consume_stock(order.part_d, to_produce)
                order.part_d.quantity_produced += to_produce
                result.feasible_orders.append(
                    ProductionOrder(part_d=order.part_d, quantity=to_produce)
                )
                result.total_produced += to_produce
                if to_produce < order.quantity:
                    # Partially fulfilled — log remainder as infeasible.
                    result.infeasible_orders.append(
                        ProductionOrder(
                            part_d=order.part_d,
                            quantity=order.quantity - to_produce,
                        )
                    )
            else:
                result.infeasible_orders.append(order)

        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compatible_parts(self, parts: list, required: Measurement) -> list:
        """Return parts whose measurement is compatible with *required*."""
        return [
            p for p in parts
            if p.measurement.is_compatible_with(required, self.tolerance) and p.stock > 0
        ]

    def _feasible_quantity(self, order: ProductionOrder) -> int:
        """
        Calculate how many units of *order.part_d* can currently be assembled.
        """
        part_d = order.part_d

        compatible_a = self._compatible_parts(self.stock.parts_a, part_d.required_measurement_a)
        compatible_b = self._compatible_parts(self.stock.parts_b, part_d.required_measurement_b)
        compatible_c = self._compatible_parts(self.stock.parts_c, part_d.required_measurement_c)

        stock_a = sum(p.stock for p in compatible_a)
        stock_b = sum(p.stock for p in compatible_b)
        stock_c = sum(p.stock for p in compatible_c)

        return min(stock_a, stock_b, stock_c)

    def _consume_stock(self, part_d: PartD, quantity: int) -> None:
        """
        Consume *quantity* units from compatible stock for assembling *part_d*.
        Parts are consumed greedily (smallest compatible stock first) to spread
        usage across multiple suppliers/batches.
        """
        self._consume_from(self.stock.parts_a, part_d.required_measurement_a, quantity)
        self._consume_from(self.stock.parts_b, part_d.required_measurement_b, quantity)
        self._consume_from(self.stock.parts_c, part_d.required_measurement_c, quantity)

    def _consume_from(self, parts: list, required: Measurement, quantity: int) -> None:
        """Consume *quantity* units from *parts* matching *required* measurement."""
        compatible = self._compatible_parts(parts, required)
        # Sort ascending by stock so we drain smaller batches first.
        compatible.sort(key=lambda p: p.stock)
        remaining = quantity
        for part in compatible:
            if remaining <= 0:
                break
            to_take = min(part.stock, remaining)
            part.consume(to_take)
            remaining -= to_take
