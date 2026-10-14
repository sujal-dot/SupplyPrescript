"""
SupplyPrescript — Optimization Decision Variables
=================================================
Defines the mathematical decision variables for the prescriptive optimization engine.
Distinguishes input parameters from controllable decisions.

Decision Variables:
- q[s, p, m]: Quantity of product p purchased from supplier s shipped via mode m (non-negative integer/continuous)
- I[p]: Ending inventory of product p after demand fulfillment (non-negative integer/continuous)
- u[p]: Unmet demand (shortage) for product p (non-negative integer/continuous)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

import pulp

from optimization.config import ScenarioConfig

logger = logging.getLogger("optimization.variables")


@dataclass
class CandidateOption:
    """
    Represents an eligible (supplier, product, transport_mode) procurement and shipping option
    with resolved operational parameters from the database and ML predictions.
    """
    supplier_id: str
    supplier_name: str
    product_id: str
    product_name: str
    transport_mode: str
    unit_cost: float
    shipping_cost_per_unit: float
    lead_time_days: float
    predicted_delay_probability: float
    predicted_delay_days: float
    expected_delay_cost_per_unit: float
    supplier_capacity: float
    origin: str = "OriginHub"
    destination: str = "Delhi"
    distance_km: float = 1000.0


@dataclass
class ProductData:
    """
    Represents product demand, initial inventory, and holding parameters.
    """
    product_id: str
    product_name: str
    starting_inventory: float
    demand: float
    unit_cost: float
    holding_cost_per_unit: float
    shortage_penalty_per_unit: float
    minimum_inventory: float = 0.0


@dataclass
class OptimizationVariables:
    """
    Container for PuLP decision variables created for a specific optimization problem instance.
    """
    # q[s, p, m] -> Quantity procured from supplier s for product p via transport mode m
    q: Dict[Tuple[str, str, str], pulp.LpVariable] = field(default_factory=dict)

    # I[p] -> Ending inventory of product p
    I: Dict[str, pulp.LpVariable] = field(default_factory=dict)

    # u[p] -> Unmet demand (shortage) for product p
    u: Dict[str, pulp.LpVariable] = field(default_factory=dict)

    # Metadata tracking
    candidate_keys: List[Tuple[str, str, str]] = field(default_factory=list)
    product_ids: List[str] = field(default_factory=list)
    supplier_ids: List[str] = field(default_factory=list)
    transport_modes: List[str] = field(default_factory=list)

    def get_procured_for_product(self, product_id: str) -> pulp.LpAffineExpression:
        """Sum of all procured quantities for product p across all suppliers and modes."""
        matching = [var for (s, p, m), var in self.q.items() if p == product_id]
        return pulp.lpSum(matching) if matching else 0.0

    def get_procured_from_supplier(self, supplier_id: str) -> pulp.LpAffineExpression:
        """Sum of all procured quantities from supplier s across all products and modes."""
        matching = [var for (s, p, m), var in self.q.items() if s == supplier_id]
        return pulp.lpSum(matching) if matching else 0.0

    def get_procured_by_mode(self, mode: str) -> pulp.LpAffineExpression:
        """Sum of all procured quantities moved by transport mode m."""
        matching = [var for (s, p, m), var in self.q.items() if m == mode]
        return pulp.lpSum(matching) if matching else 0.0


def create_decision_variables(
    problem: pulp.LpProblem,
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> OptimizationVariables:
    """
    Instantiate decision variables in the given PuLP problem instance.
    Ensures non-negativity and adheres to configured variable categories (Integer vs Continuous).
    """
    cat = "Integer" if config.optimization.integer_quantities else "Continuous"

    variables = OptimizationVariables()
    supplier_set: Set[str] = set()
    product_set: Set[str] = set()
    mode_set: Set[str] = set()

    # 1. Procurement and Shipping Variables q[s, p, m]
    for opt in candidate_options:
        key = (opt.supplier_id, opt.product_id, opt.transport_mode)
        # Variable name cleaned for solver syntax compatibility
        var_name = f"q_{opt.supplier_id}_{opt.product_id}_{opt.transport_mode}".replace("-", "_").replace(" ", "_")

        # Upper bound by individual supplier capacity if available
        up_bound = opt.supplier_capacity if opt.supplier_capacity > 0 else None

        # Create variable on problem (PuLP 4.0 / 3.x compatible)
        if hasattr(problem, "add_variable"):
            var = problem.add_variable(var_name, lowBound=0, upBound=up_bound, cat=cat)
        else:
            var = pulp.LpVariable(var_name, lowBound=0, upBound=up_bound, cat=cat)

        variables.q[key] = var
        variables.candidate_keys.append(key)
        supplier_set.add(opt.supplier_id)
        product_set.add(opt.product_id)
        mode_set.add(opt.transport_mode)

    # 2. Inventory and Shortage Variables for each product
    for prod in products:
        p_id = prod.product_id
        product_set.add(p_id)

        # Ending Inventory I[p] >= 0
        inv_name = f"I_{p_id}".replace("-", "_").replace(" ", "_")
        if hasattr(problem, "add_variable"):
            var_inv = problem.add_variable(inv_name, lowBound=0, cat=cat)
        else:
            var_inv = pulp.LpVariable(inv_name, lowBound=0, cat=cat)
        variables.I[p_id] = var_inv

        # Shortage u[p] >= 0 (bounded by demand)
        short_name = f"u_{p_id}".replace("-", "_").replace(" ", "_")
        up_shortage = prod.demand if prod.demand > 0 else 0
        if not config.optimization.allow_shortage:
            up_shortage = 0  # Force zero shortage if not allowed

        if hasattr(problem, "add_variable"):
            var_short = problem.add_variable(short_name, lowBound=0, upBound=up_shortage, cat=cat)
        else:
            var_short = pulp.LpVariable(short_name, lowBound=0, upBound=up_shortage, cat=cat)
        variables.u[p_id] = var_short

    variables.supplier_ids = sorted(list(supplier_set))
    variables.product_ids = sorted(list(product_set))
    variables.transport_modes = sorted(list(mode_set))

    logger.debug(
        "Created %d procurement variables, %d inventory variables, %d shortage variables.",
        len(variables.q),
        len(variables.I),
        len(variables.u),
    )
    return variables
