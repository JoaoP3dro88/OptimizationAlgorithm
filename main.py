"""
Entry point – demonstrates the production optimizer with a sample scenario.

Run with:
    python main.py
"""

from src.models import Measurement, PartA, PartB, PartC, PartD, Stock
from src.optimizer import ProductionOptimizer, ProductionOrder


def build_sample_stock() -> Stock:
    """Create a sample stock with several Part A / B / C variants."""
    stock = Stock()

    # ---- Part A variants ----
    stock.add_part_a(PartA(measurement=Measurement(100, 50, 20), stock=10))
    stock.add_part_a(PartA(measurement=Measurement(200, 80, 30), stock=5))

    # ---- Part B variants ----
    stock.add_part_b(PartB(measurement=Measurement(60, 40, 15), stock=8))
    stock.add_part_b(PartB(measurement=Measurement(120, 60, 25), stock=3))

    # ---- Part C variants ----
    stock.add_part_c(PartC(measurement=Measurement(30, 30, 10), stock=12))
    stock.add_part_c(PartC(measurement=Measurement(90, 45, 20), stock=4))

    return stock


def build_sample_orders() -> list:
    """Define several Part D production orders with different measurement requirements."""
    # Part D variant 1 — uses the most common (small) components
    d1 = PartD(
        name="Part D – Small",
        required_measurement_a=Measurement(100, 50, 20),
        required_measurement_b=Measurement(60, 40, 15),
        required_measurement_c=Measurement(30, 30, 10),
    )

    # Part D variant 2 — uses the larger components
    d2 = PartD(
        name="Part D – Large",
        required_measurement_a=Measurement(200, 80, 30),
        required_measurement_b=Measurement(120, 60, 25),
        required_measurement_c=Measurement(90, 45, 20),
    )

    return [
        ProductionOrder(part_d=d1, quantity=7),
        ProductionOrder(part_d=d2, quantity=5),
    ]


def main() -> None:
    stock = build_sample_stock()
    orders = build_sample_orders()

    print("=== Initial Stock ===")
    for part_name, qty in stock.summary().items():
        print(f"  {part_name}: {qty} unit(s)")

    optimizer = ProductionOptimizer(stock=stock, tolerance=0.0)
    result = optimizer.optimize(orders)

    print()
    print(result.summary())

    print()
    print("=== Remaining Stock ===")
    for part_name, qty in stock.summary().items():
        print(f"  {part_name}: {qty} unit(s)")


if __name__ == "__main__":
    main()
