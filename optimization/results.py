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
    expected_delay_days: float = 0.0
    expected_delay_probability: float = 0.0
    predicted_delay: Optional[float] = None
    total_procurement_cost: float = 0.0
    total_shipping_cost: float = 0.0
    expected_delay_cost: float = 0.0
    expected_risk_cost: float = 0.0
    total_cost: float = 0.0
    estimated_cost: Optional[float] = None

    def model_post_init(self, __context: Any) -> None:
        if self.predicted_delay is None:
            self.predicted_delay = self.expected_delay_days
        if self.estimated_cost is None:
            self.estimated_cost = self.total_cost


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
    status: str = Field(..., description="Solver outcome status (OPTIMAL, FEASIBLE, INFEASIBLE, UNBOUNDED, TIME_LIMIT, ERROR)")
    scenario_id: str = Field("baseline", description="Unique scenario identifier")
    scenario_name: str = Field("baseline", description="Human-readable scenario name")
    objective_value: Optional[float] = Field(None, description="Total minimized cost computed by solver (null if infeasible/failed)")
    currency: str = Field("USD", description="Currency code (e.g. USD)")
    cost_breakdown: Dict[str, Optional[float]] = Field(
        default_factory=lambda: {
            "procurement_cost": None,
            "shipping_cost": None,
            "inventory_cost": None,
            "delay_penalty": None,
            "risk_cost": None,
            "shortage_cost": None,
        },
        description="Granular component costs computed by the engine",
    )
    decisions: List[DecisionAllocation] = Field(default_factory=list)
    constraint_checks: List[ConstraintCheckResult] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    model_metadata: Dict[str, Any] = Field(
        default_factory=lambda: {
            "solver": None,
            "model_version": None,
        },
        description="Solver engine, active ML version, solve duration, and execution metadata",
    )

    # Backwards-compatible fields for Day 11 callers
    solver_name: str = "Unknown"
    solve_time_seconds: float = 0.0
    objective: ObjectiveSummary = Field(default_factory=ObjectiveSummary)
    constraints: Optional[ConstraintSummary] = None
    inventory_summary: List[InventoryResult] = Field(default_factory=list)
    supplier_utilization: List[SupplierCapacityUtilization] = Field(default_factory=list)
    budget_utilization_pct: Optional[float] = None
    infeasibility_diagnostics: Optional[InfeasibilityReport] = None

    def is_optimal(self) -> bool:
        """Only returns True when solver confirms mathematical optimality."""
        return self.status.upper() == "OPTIMAL"

    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary matching Day 12 structured JSON specifications."""
        return self.model_dump()
