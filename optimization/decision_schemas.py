"""
SupplyPrescript — Decision Schemas & Domain Models
===================================================
Pydantic data schemas for alternative supply-chain decisions, baseline summaries,
independent solution validation, and structured prescriptive recommendation responses.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FeasibilityStatus(str, Enum):
    FEASIBLE = "FEASIBLE"
    INFEASIBLE = "INFEASIBLE"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


class RecommendationStatus(str, Enum):
    FEASIBLE_RECOMMENDATION = "FEASIBLE_RECOMMENDATION"
    NO_FEASIBLE_OPTION = "NO_FEASIBLE_OPTION"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    ERROR = "ERROR"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class ConstraintViolation(BaseModel):
    constraint_name: str = Field(..., description="Name of the violated constraint (e.g. Budget, Capacity, Delivery)")
    limit_value: float = Field(..., description="Configured ceiling or floor threshold")
    actual_value: float = Field(..., description="Calculated actual value of the candidate solution")
    violation_amount: float = Field(..., description="Absolute extent of constraint violation")
    message: str = Field(..., description="Human-readable explanation of the constraint failure")


class AlternativeOption(BaseModel):
    option_id: str = Field(..., description="Alternative identifier (e.g. 'A', 'B', 'C')")
    name: str = Field(..., description="Name of alternative (e.g. 'Air Freight', 'Secondary Supplier', 'Delay Product Launch')")
    feasibility: FeasibilityStatus = Field(..., description="Operational feasibility status")
    estimated_total_cost: Optional[float] = Field(None, description="Total supply-chain expenditure under this option ($)")
    additional_cost: Optional[float] = Field(None, description="Incremental cost relative to baseline ($)")
    additional_cost_percentage: Optional[float] = Field(None, description="Percentage cost difference relative to baseline (%)")
    estimated_delivery_days: Optional[float] = Field(None, description="Total expected transit and arrival duration in days")
    schedule_impact_days: Optional[float] = Field(None, description="Net delivery impact relative to baseline (+ days delayed, - days expedited)")
    delay_probability: Optional[float] = Field(None, description="ML predicted probability of shipment delay [0.0 - 1.0]")
    predicted_delay_days: Optional[float] = Field(None, description="ML predicted delay duration beyond planned lead time (days)")
    risk_level: Optional[RiskLevel] = Field(None, description="Categorical risk tier (LOW, MEDIUM, HIGH, UNKNOWN)")
    objective_value: Optional[float] = Field(None, description="Day 12 composite objective value Z = C_total + C_delay + C_risk")
    supplier_id: Optional[str] = Field(None, description="Identifier of the executing supplier")
    supplier_name: Optional[str] = Field(None, description="Name of the executing supplier")
    transport_mode: Optional[str] = Field(None, description="Mode of transport (Air, Road, Rail, Sea)")
    cost_breakdown: Dict[str, Optional[float]] = Field(default_factory=dict, description="Itemized costs: procurement, shipping, holding, delay, risk")
    constraint_violations: List[ConstraintViolation] = Field(default_factory=list, description="List of violated business constraints if infeasible")
    assumptions: List[str] = Field(default_factory=list, description="Key assumptions and operational data inputs used")
    explanation: str = Field("", description="Detailed business explanation of advantages, drawbacks, and consequences")
    is_recommended: bool = Field(False, description="True if this alternative is chosen as the optimal recommendation")
    trade_offs: Optional[str] = Field(None, description="Summary of service vs cost vs risk trade-offs")


class BaselineSummary(BaseModel):
    shipment_id: str = Field(..., description="Original shipment identifier")
    product_id: str = Field(..., description="Product SKU identifier")
    product_name: str = Field(..., description="Product display name")
    supplier_id: str = Field(..., description="Original supplier identifier")
    supplier_name: str = Field(..., description="Original supplier display name")
    transport_mode: str = Field(..., description="Original planned transport mode")
    quantity: float = Field(..., description="Order volume in units")
    unit_cost: float = Field(..., description="Base product procurement cost per unit ($)")
    shipping_cost: float = Field(..., description="Original total transport freight cost ($)")
    estimated_total_cost: Optional[float] = Field(None, description="Original total baseline expenditure ($)")
    predicted_delay_probability: float = Field(0.0, description="ML predicted baseline delay probability")
    predicted_delay_days: float = Field(0.0, description="ML predicted baseline delay duration in days")
    risk_level: str = Field("LOW", description="Baseline risk category")
    planned_lead_time_days: float = Field(0.0, description="Nominal supplier transit lead time in days")
    total_delivery_days: float = Field(0.0, description="Total expected arrival duration (lead time + predicted delay)")
    currency: str = Field("USD", description="Currency denomination")


class SolutionValidationReport(BaseModel):
    is_valid: bool = Field(..., description="True if all hard business constraints are satisfied within tolerance")
    is_eligible_for_recommendation: bool = Field(..., description="True if solution can safely be presented as a recommendation")
    budget_passed: bool = Field(True, description="Budget constraint check outcome")
    capacity_passed: bool = Field(True, description="Supplier capacity constraint check outcome")
    inventory_passed: bool = Field(True, description="Inventory balance constraint check outcome")
    delivery_passed: bool = Field(True, description="Delivery delay constraint check outcome")
    violations: List[ConstraintViolation] = Field(default_factory=list, description="Constraint violation details")
    slacks: Dict[str, float] = Field(default_factory=dict, description="Constraint slack margins (positive = within limit)")


class AlternativeEvaluationResponse(BaseModel):
    shipment_id: str = Field(..., description="Shipment evaluated")
    scenario_id: str = Field("baseline", description="Planning scenario identifier")
    baseline: BaselineSummary = Field(..., description="Baseline shipment and performance metrics")
    alternatives: List[AlternativeOption] = Field(..., description="The three evaluated decision alternatives (A, B, C)")
    recommended_option_id: Optional[str] = Field(None, description="Winning option ID ('A', 'B', 'C') or null if none eligible")
    recommendation_status: RecommendationStatus = Field(..., description="Overall recommendation resolution status")
    recommendation_reason: str = Field("", description="Justification for the chosen option or reason for failure")
    trade_off_analysis: str = Field("", description="Comparative trade-off synthesis across cost, delay, and risk")
    model_version: Optional[str] = Field(None, description="Active ML model version used for inference")
    warnings: List[str] = Field(default_factory=list, description="Audit warnings or missing data indicators")
    evaluated_at: str = Field(..., description="ISO 8601 evaluation timestamp")


class AlternativeGenerationRequest(BaseModel):
    shipment_id: str = Field(..., description="Authoritative shipment ID to generate alternatives for (e.g. 'SHIP001')")
    scenario_overrides: Optional[Dict[str, Any]] = Field(None, description="Optional runtime scenario parameter overrides")
    save_to_database: bool = Field(False, description="Whether to persist generated recommendation to PostgreSQL database")


# ===========================================================================
# Day 14 Production Optimization API Schemas (POST /api/optimize)
# ===========================================================================

class OptimizationRequest(BaseModel):
    shipment_id: str = Field(
        ...,
        min_length=1,
        description="Target shipment identifier (e.g. 'SHP1023' or 'SHIP001')",
        examples=["SHP1023", "SHIP001"],
    )
    scenario_id: str = Field(
        "baseline",
        description="Supported optimization scenario (e.g. 'baseline', 'budget_constrained', 'delay_sensitive')",
    )
    num_options: int = Field(
        3,
        ge=1,
        le=10,
        description="Maximum number of distinct candidate decisions to return (default 3)",
    )
    scenario_overrides: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional trusted runtime parameters (e.g. budget ceilings, delay limits)",
    )


class OptimizationPredictionSummary(BaseModel):
    delay_probability: float = Field(..., ge=0.0, le=1.0, description="Active ML predicted delay probability")
    predicted_delay_days: float = Field(..., ge=0.0, description="Active ML predicted delay duration in days")
    risk_level: str = Field(..., description="Categorical risk tier: LOW, MEDIUM, or HIGH")
    model_version: str = Field("v1.0", description="Registered model version used for inference")


class OptimizationConstraintCheck(BaseModel):
    name: str = Field(..., description="Constraint identifier (e.g. Maximum Budget, Supplier Capacity)")
    status: str = Field(..., description="Audit outcome: SATISFIED, BINDING, or VIOLATED")
    lhs_value: float = Field(..., description="Evaluated left-hand-side value of candidate plan")
    rhs_value: float = Field(..., description="Configured right-hand-side threshold limit")
    slack: float = Field(..., description="Slack margin: positive indicates headroom, negative indicates violation")
    description: Optional[str] = Field(None, description="Explanation of constraint verification")


class OptimizationMetadata(BaseModel):
    scenario_id: str = Field("baseline", description="Applied scenario name")
    solver_status: Optional[str] = Field("OPTIMAL", description="Status returned by prescriptive optimization engine")
    runtime_ms: Optional[float] = Field(None, description="Total pipeline execution time in milliseconds")
    model_version: Optional[str] = Field("v1.0", description="Active ML version")


class OptimizationOption(BaseModel):
    option_id: str = Field(..., description="Unique option identifier ('A', 'B', 'C')")
    strategy: str = Field(..., description="Strategy category: AIR_FREIGHT, SECONDARY_SUPPLIER, or DELAY_LAUNCH")
    name: str = Field(..., description="Descriptive strategy title")
    status: str = Field(..., description="Feasibility classification: FEASIBLE, INFEASIBLE, INSUFFICIENT_DATA, ERROR")
    estimated_total_cost: Optional[float] = Field(None, description="Total supply-chain expenditure under this option ($)")
    additional_cost: Optional[float] = Field(None, description="Incremental expenditure relative to baseline plan ($)")
    estimated_delivery_days: Optional[float] = Field(None, description="Total expected transit and arrival duration in days")
    delay_probability: Optional[float] = Field(None, description="Delay probability under this strategy")
    risk_level: Optional[str] = Field(None, description="Risk classification")
    objective_value: Optional[float] = Field(None, description="Day 12 composite objective score Z")
    constraint_violations: List[ConstraintViolation] = Field(default_factory=list, description="Violated constraints if any")
    assumptions: List[str] = Field(default_factory=list, description="Key operational assumptions")
    explanation: str = Field("", description="Business rationale, trade-offs, and consequences")
    is_recommended: bool = Field(False, description="True if selected as the optimal recommendation")


class OptimizationResponse(BaseModel):
    shipment_id: str = Field(..., description="Target shipment identifier")
    status: str = Field(..., description="Top-level status: SUCCESS, NO_FEASIBLE_OPTION, INSUFFICIENT_DATA, ERROR")
    prediction: OptimizationPredictionSummary = Field(..., description="Active ML delay risk assessment")
    options: List[OptimizationOption] = Field(..., description="Ranked decision alternatives (at most num_options)")
    recommended_option_id: Optional[str] = Field(None, description="Winning option ID or null if no feasible option exists")
    recommendation_reason: str = Field("", description="Justification for recommendation or root causes for failure")
    constraint_checks: List[OptimizationConstraintCheck] = Field(default_factory=list, description="Constraint checks")
    warnings: List[str] = Field(default_factory=list, description="Audit warnings or missing data notices")
    optimization_metadata: OptimizationMetadata = Field(default_factory=OptimizationMetadata, description="Execution telemetry")

