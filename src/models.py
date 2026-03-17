"""Data models for production parts A, B, C and assembled product D."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Measurement:
    """Physical measurement of a part (e.g. length, width, height in mm)."""

    length: float
    width: float
    height: float

    def __repr__(self) -> str:
        return f"Measurement(length={self.length}, width={self.width}, height={self.height})"

    def is_compatible_with(self, other: "Measurement", tolerance: float = 0.0) -> bool:
        """Return True if this measurement is within tolerance of another."""
        return (
            abs(self.length - other.length) <= tolerance
            and abs(self.width - other.width) <= tolerance
            and abs(self.height - other.height) <= tolerance
        )


@dataclass
class Part:
    """Base class representing a production part with a measurement and stock quantity."""

    measurement: Measurement
    name: str = ""
    stock: int = 0

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, measurement={self.measurement}, stock={self.stock})"

    def consume(self, quantity: int = 1) -> None:
        """Reduce stock by *quantity*. Raises ValueError if stock is insufficient."""
        if quantity > self.stock:
            raise ValueError(
                f"Not enough stock for {self.name}: requested {quantity}, available {self.stock}"
            )
        self.stock -= quantity

    def replenish(self, quantity: int) -> None:
        """Add *quantity* units to stock."""
        if quantity < 0:
            raise ValueError("Replenishment quantity must be non-negative.")
        self.stock += quantity


@dataclass
class PartA(Part):
    """Component part A."""

    name: str = "Part A"


@dataclass
class PartB(Part):
    """Component part B."""

    name: str = "Part B"


@dataclass
class PartC(Part):
    """Component part C."""

    name: str = "Part C"


@dataclass
class PartD:
    """
    Assembled product D.

    Part D is assembled from exactly one unit each of Parts A, B and C.
    The required measurements for each component can be set independently
    to match the desired specification of each Part D variant.
    """

    name: str
    required_measurement_a: Measurement
    required_measurement_b: Measurement
    required_measurement_c: Measurement
    quantity_produced: int = 0

    def __repr__(self) -> str:
        return (
            f"PartD(name={self.name!r}, "
            f"req_A={self.required_measurement_a}, "
            f"req_B={self.required_measurement_b}, "
            f"req_C={self.required_measurement_c}, "
            f"quantity_produced={self.quantity_produced})"
        )


@dataclass
class Stock:
    """
    Container that holds the available inventory of component parts A, B and C.

    Each component is stored as a list so that parts with *different* measurements
    can coexist in the same stock.
    """

    parts_a: list = field(default_factory=list)
    parts_b: list = field(default_factory=list)
    parts_c: list = field(default_factory=list)

    def add_part_a(self, part: PartA) -> None:
        self.parts_a.append(part)

    def add_part_b(self, part: PartB) -> None:
        self.parts_b.append(part)

    def add_part_c(self, part: PartC) -> None:
        self.parts_c.append(part)

    def total_stock_a(self) -> int:
        return sum(p.stock for p in self.parts_a)

    def total_stock_b(self) -> int:
        return sum(p.stock for p in self.parts_b)

    def total_stock_c(self) -> int:
        return sum(p.stock for p in self.parts_c)

    def summary(self) -> dict:
        """Return a dict with stock totals for each component."""
        return {
            "Part A": self.total_stock_a(),
            "Part B": self.total_stock_b(),
            "Part C": self.total_stock_c(),
        }
