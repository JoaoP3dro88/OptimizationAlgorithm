# OptimizationAlgorithm

A basic optimization algorithm that finds the best production sequence for **Part D** — a product assembled from component parts **A**, **B** and **C** — based on the current stock volume of each component.

---

## Problem

Part D is assembled by combining one unit each of Parts A, B and C.  
Each part has specific physical **measurements** (length × width × height).  
Given a list of production orders and the current component inventory, the optimizer determines:

1. Which Part D orders can be fulfilled (and how many units).
2. The optimal **production sequence** that maximises total throughput.
3. Which orders cannot be satisfied with the available stock.

---

## Project Structure

```
OptimizationAlgorithm/
├── main.py               # Entry point – sample scenario
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── models.py         # Measurement, PartA/B/C, PartD, Stock
│   └── optimizer.py      # ProductionOptimizer, ProductionOrder, OptimizationResult
└── tests/
    ├── test_models.py
    └── test_optimizer.py
```

---

## Key Concepts

| Class | Description |
|---|---|
| `Measurement` | Physical dimensions of a part (length, width, height in mm). Supports tolerance-based compatibility checks. |
| `PartA` / `PartB` / `PartC` | Component parts with a measurement and a stock quantity. |
| `PartD` | Assembled product specifying the required measurements for each component. |
| `Stock` | Inventory container holding lists of Part A, B and C (multiple measurement variants per component are supported). |
| `ProductionOrder` | A request to produce N units of a specific Part D variant. |
| `ProductionOptimizer` | Scores each order by achievable quantity given current stock, sorts orders to maximise throughput, simulates production and returns an `OptimizationResult`. |
| `OptimizationResult` | Contains the optimised sequence, feasible orders, infeasible orders and total units produced. |

---

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the sample scenario
python main.py
```

### Example output

```
=== Initial Stock ===
  Part A: 15 unit(s)
  Part B: 11 unit(s)
  Part C: 16 unit(s)

=== Optimization Result ===
Total Part D units produced : 10
Feasible orders (2):
  - Part D – Small: 7 unit(s)
  - Part D – Large: 3 unit(s)
Infeasible orders (1) - insufficient stock:
  - Part D – Large: 2 unit(s) requested

=== Remaining Stock ===
  Part A: 5 unit(s)
  Part B: 1 unit(s)
  Part C: 6 unit(s)
```

---

## Running Tests

```bash
python -m pytest tests/ -v
```

---

## Optimization Strategy

1. **Score** – For each production order, calculate the maximum feasible quantity: `min(compatible_stock_A, compatible_stock_B, compatible_stock_C)`.
2. **Sort** – Rank orders by feasible quantity (descending) to favour the most productive orders first.
3. **Simulate** – Consume stock greedily (smallest batches first to spread usage) and record fulfilled / unfulfilled quantities.
