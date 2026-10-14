"""
SupplyPrescript — Optimization Result Schema
============================================
Pydantic schemas and serialization models for optimization outputs.
Structures solver status, cost breakdowns, procurement allocations,
ending inventories, constraint slack audits, and infeasibility diagnostics.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger("optimization.results")


class ObjectiveSummary(BaseModel):
    name: str = Field("minimize_total_cost", description="Name of the optimization objective")
    total_cost: Optional[float] = Field(None, description="Total minimized supply-chain cost in configured currency")
    currency: str = Field("USD", description="Currency denominator (e.g. USD)")
    cost_breakdown: Optional[Dict[str, float]] = Field(
        None,
        description="Detailed breakdown by cost component: procurement, shipping, holding, delay, shortage",
    )


class ConstraintSummary(BaseModel):
    budget_limit: float = Field(..., description="Configured cash budget ceiling ($)")
    minimum_inventory_units: float = Field(..., description="Minimum aggregate ending inventory target (units)")
    maximum_acceptable_delay_days: float = Field(..., description="Configured delay tolerance threshold (days)")
    default_supplier_capacity_units: float = Field(..., description="Default maximum capacity per supplier (units)")


class DecisionAllocation(BaseModel):
    supplier_id: str
    supplier_name: str
    product_id: str
    product_name: str
    transport_mode: str
    quantity: float
    unit_cost: float
    shipping_cost_per_unit: float
    expected_delay_days: float
    expected_delay_probability: float
    total_procurement_cost: float
    total_shipping_cost: float
    expected_delay_cost: float
    total_cost: float


class InventoryResult(BaseModel):
    product_id: str
    product_name: str
    starting_inventory: float
    procured_quantity: float
    demand: float
    ending_inventory: float
    shortage_quantity: float
    holding_cost: float


class ConstraintCheckResult(BaseModel):
    name: str
    category: str
    status: str = Field(..., description="Status: 'SATISFIED', 'BINDING', or 'VIOLATED'")
    lhs_value: float
    rhs_value: float
    slack: float
    description: str


class SupplierCapacityUtilization(BaseModel):
    supplier_id: str
    allocated_units: float
    max_capacity_units: float
    utilization_pct: float
    remaining_capacity: float


class InfeasibilityReport(BaseModel):
    is_infeasible: bool = True
    conflicting_constraints: List[str] = Field(default_factory=list)
    root_causes: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    scenario_name: str
    status: str = Field(..., description="Solver outcome status (OPTIMAL, INFEASIBLE, UNBOUNDED, TIME_LIMIT, ERROR)")
    solver_name: str
    solve_time_seconds: float = 0.0
    objective: ObjectiveSummary
    constraints: ConstraintSummary
    decisions: List[DecisionAllocation] = Field(default_factory=list)
    inventory_summary: List[InventoryResult] = Field(default_factory=list)
    constraint_checks: List[ConstraintCheckResult] = Field(default_factory=list)
    supplier_utilization: List[SupplierCapacityUtilization] = Field(default_factory=list)
    budget_utilization_pct: Optional[float] = None
    warnings: List[str] = Field(default_factory=list)
    infeasibility_diagnostics: Optional[InfeasibilityReport] = None

    def is_optimal(self) -> bool:
        return self.status.upper() == "OPTIMAL"

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
