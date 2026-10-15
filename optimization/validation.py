"""
SupplyPrescript — Optimization Validation and Infeasibility Diagnostics
========================================================================
Validates optimization inputs prior to solver execution and analyzes mathematical
infeasibility conflicts post-solve.

Provides pre-solve sanity checks:
- Positive budget limit
- Non-negative capacities, initial inventories, and demands
- Consistent currency and non-negative unit costs
- Viability of delivery thresholds

Provides post-solve root-cause conflict analysis:
- Capacity bottlenecks
- Budget deficits
- Delivery deadline conflicts
- Incompatible inventory conservation requirements
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from optimization.config import ScenarioConfig
from optimization.variables import CandidateOption, ProductData

logger = logging.getLogger("optimization.validation")


class ValidationError(ValueError):
    """Raised when pre-solve validation encounters invalid or corrupted business parameters."""
    pass


@dataclass
class PreSolveValidationReport:
    """Detailed report from pre-solve input verification."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    total_demand: float = 0.0
    total_starting_inventory: float = 0.0
    total_supplier_capacity: float = 0.0
    min_required_procurement: float = 0.0
    estimated_min_cost: float = 0.0


@dataclass
class InfeasibilityDiagnostic:
    """Diagnostic report explaining why a scenario could not be solved to optimality."""
    is_infeasible: bool
    conflicting_constraints: List[str] = field(default_factory=list)
    root_causes: List[str] = field(default_factory=list)
    suggested_actions: List[str] = field(default_factory=list)
    slack_analysis: Dict[str, float] = field(default_factory=dict)


def validate_optimization_inputs(
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> PreSolveValidationReport:
    """
    Perform thorough pre-solve consistency and domain validation.
    Detects impossible scenarios before invoking solver routines.
    """
    errors: List[str] = []
    warnings: List[str] = []

    # 1. Configuration Sanity
    if config.budget.max_total_cost <= 0:
        errors.append(f"Budget must be strictly positive. Received: {config.budget.max_total_cost}")

    if config.inventory.minimum_required_units < 0:
        errors.append(f"Minimum inventory requirement cannot be negative. Received: {config.inventory.minimum_required_units}")

    if config.delivery.maximum_acceptable_delay_days < 0:
        errors.append(f"Maximum acceptable delay days cannot be negative. Received: {config.delivery.maximum_acceptable_delay_days}")

    # 2. Product and Demand Consistency
    if not products:
        errors.append("No products supplied to optimization problem.")

    product_ids = set()
    total_demand = 0.0
    total_starting_inv = 0.0

    for prod in products:
        if prod.product_id in product_ids:
            errors.append(f"Duplicate product_id encountered: '{prod.product_id}'")
        product_ids.add(prod.product_id)

        if prod.demand < 0:
            errors.append(f"Product '{prod.product_id}' has negative demand: {prod.demand}")
        if prod.starting_inventory < 0:
            errors.append(f"Product '{prod.product_id}' has negative starting inventory: {prod.starting_inventory}")
        if prod.unit_cost < 0:
            errors.append(f"Product '{prod.product_id}' has negative unit cost: {prod.unit_cost}")
        if prod.holding_cost_per_unit < 0:
            errors.append(f"Product '{prod.product_id}' has negative holding cost: {prod.holding_cost_per_unit}")

        total_demand += max(0.0, prod.demand)
        total_starting_inv += max(0.0, prod.starting_inventory)

    # 3. Candidate Options & Supplier Consistency
    if not candidate_options:
        errors.append("No eligible candidate procurement/shipping options available.")

    supplier_capacities: Dict[str, float] = {}
    options_by_product: Dict[str, List[CandidateOption]] = {p.product_id: [] for p in products}

    for opt in candidate_options:
        if opt.product_id not in product_ids:
            errors.append(f"Candidate option references unknown product_id: '{opt.product_id}'")
        else:
            options_by_product[opt.product_id].append(opt)

        if opt.unit_cost < 0:
            errors.append(f"Option ({opt.supplier_id}, {opt.product_id}, {opt.transport_mode}) has negative unit cost: {opt.unit_cost}")
        if opt.shipping_cost_per_unit < 0:
            errors.append(f"Option ({opt.supplier_id}, {opt.product_id}, {opt.transport_mode}) has negative shipping cost: {opt.shipping_cost_per_unit}")
        if opt.supplier_capacity < 0:
            errors.append(f"Supplier '{opt.supplier_id}' has negative capacity: {opt.supplier_capacity}")
        if not (0.0 <= opt.predicted_delay_probability <= 1.0):
            errors.append(f"Option ({opt.supplier_id}, {opt.product_id}, {opt.transport_mode}) has invalid delay probability outside [0, 1]: {opt.predicted_delay_probability}")
        if hasattr(opt, "supplier_reliability") and not (0.0 <= opt.supplier_reliability <= 1.0):
            errors.append(f"Supplier '{opt.supplier_id}' has invalid reliability score outside [0, 1]: {opt.supplier_reliability}")
        if opt.predicted_delay_days < 0:
            errors.append(f"Option ({opt.supplier_id}, {opt.product_id}, {opt.transport_mode}) has negative predicted delay days: {opt.predicted_delay_days}")

        if opt.supplier_id not in supplier_capacities:
            supplier_capacities[opt.supplier_id] = opt.supplier_capacity

    total_capacity = sum(supplier_capacities.values())

    # 4. Check for orphan products with no valid candidate routes
    for prod_id, opts in options_by_product.items():
        if not opts:
            errors.append(f"Product '{prod_id}' has zero candidate supplier options.")
        else:
            # Check if all options violate delay threshold
            valid_delay_opts = [
                o for o in opts if o.predicted_delay_days <= config.delivery.maximum_acceptable_delay_days
            ]
            if not valid_delay_opts:
                warnings.append(
                    f"Product '{prod_id}' has NO candidate options satisfying maximum acceptable delay "
                    f"<= {config.delivery.maximum_acceptable_delay_days:.1f} days."
                )

    # 5. Theoretical Feasibility Checks
    # Net procurement required = max(0, total_demand + minimum_required_inventory - total_starting_inventory)
    net_procurement_needed = max(0.0, (total_demand + config.inventory.minimum_required_units) - total_starting_inv)

    if net_procurement_needed > total_capacity and not config.optimization.allow_shortage:
        errors.append(
            f"Definite Infeasibility: Net required units ({net_procurement_needed:.1f}) exceeds "
            f"total aggregate supplier capacity ({total_capacity:.1f}) with zero shortage permitted."
        )

    # Minimal theoretical procurement spend
    cheapest_unit_prices = [
        min([o.unit_cost + o.shipping_cost_per_unit for o in opts])
        for opts in options_by_product.values()
        if opts
    ]
    avg_cheapest_cost = (sum(cheapest_unit_prices) / len(cheapest_unit_prices)) if cheapest_unit_prices else 0.0
    estimated_min_spend = net_procurement_needed * avg_cheapest_cost

    if estimated_min_spend > config.budget.max_total_cost and not config.optimization.allow_shortage:
        warnings.append(
            f"High Risk of Budget Infeasibility: Estimated minimum spend ({estimated_min_spend:,.2f} {config.budget.currency}) "
            f"exceeds total budget limit ({config.budget.max_total_cost:,.2f} {config.budget.currency})."
        )

    report = PreSolveValidationReport(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        total_demand=total_demand,
        total_starting_inventory=total_starting_inv,
        total_supplier_capacity=total_capacity,
        min_required_procurement=net_procurement_needed,
        estimated_min_cost=estimated_min_spend,
    )

    if not report.is_valid:
        logger.error("Pre-solve validation failed with %d errors: %s", len(errors), errors)
    elif warnings:
        logger.warning("Pre-solve validation completed with %d warnings: %s", len(warnings), warnings)

    return report


def diagnose_infeasibility(
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
    pre_report: PreSolveValidationReport,
) -> InfeasibilityDiagnostic:
    """
    Analyze mathematical infeasibility conflicts post-solve and produce actionable root-cause advice.
    Does NOT automatically relax constraints without explicit user authorization.
    """
    conflicts: List[str] = []
    root_causes: List[str] = []
    suggestions: List[str] = []

    # 1. Capacity vs Demand Bottleneck
    if pre_report.min_required_procurement > pre_report.total_supplier_capacity:
        deficit = pre_report.min_required_procurement - pre_report.total_supplier_capacity
        conflicts.append("Constraint_Supplier_Capacity vs Constraint_Minimum_Inventory")
        root_causes.append(
            f"Aggregate supplier capacity ({pre_report.total_supplier_capacity:,.1f} units) is insufficient to fulfill "
            f"total demand ({pre_report.total_demand:,.1f}) and minimum ending inventory "
            f"({config.inventory.minimum_required_units:,.1f}). Deficit: {deficit:,.1f} units."
        )
        suggestions.append(
            f"Consider increasing supplier capacity limits by at least {deficit:,.1f} units or reducing "
            f"the minimum inventory requirement (currently {config.inventory.minimum_required_units:,.1f} units)."
        )

    # 2. Budget Deficit
    if pre_report.estimated_min_cost > config.budget.max_total_cost:
        budget_gap = pre_report.estimated_min_cost - config.budget.max_total_cost
        conflicts.append("Constraint_Budget_Limit vs Constraint_Demand_Fulfillment")
        root_causes.append(
            f"Available budget ({config.budget.max_total_cost:,.2f} {config.budget.currency}) is lower than the "
            f"theoretical minimum procurement cost ({pre_report.estimated_min_cost:,.2f} {config.budget.currency}). "
            f"Estimated budget gap: {budget_gap:,.2f} {config.budget.currency}."
        )
        suggestions.append(
            f"Consider increasing max_total_cost budget to at least {pre_report.estimated_min_cost * 1.1:,.2f} "
            f"{config.budget.currency} or enabling shortage allowance (allow_shortage: true)."
        )

    # 3. Delivery Deadline & Lead Time Conflicts
    max_delay = config.delivery.maximum_acceptable_delay_days
    excessive_delay_opts = [
        o for o in candidate_options if o.predicted_delay_days > max_delay
    ]
    if len(excessive_delay_opts) == len(candidate_options) and candidate_options:
        conflicts.append("Constraint_Delivery_Deadline")
        root_causes.append(
            f"Every single available transportation route has a predicted delay exceeding the maximum acceptable "
            f"threshold ({max_delay:.1f} days)."
        )
        min_available_delay = min([o.predicted_delay_days for o in candidate_options])
        suggestions.append(
            f"Consider relaxing maximum_acceptable_delay_days from {max_delay:.1f} to at least "
            f"{min_available_delay + 0.5:.1f} days or onboarding suppliers with expedited transit."
        )

    if not conflicts:
        conflicts.append("Simultaneous_Coupled_Constraints")
        root_causes.append(
            "The simultaneous intersection of supplier capacities, budget limitation, and minimum inventory "
            "leaves no feasible integer solution."
        )
        suggestions.append(
            "Review parameter sensitivity: incrementally test relaxed budget (+25%) or reduced inventory targets (-25%)."
        )

    return InfeasibilityDiagnostic(
        is_infeasible=True,
        conflicting_constraints=conflicts,
        root_causes=root_causes,
        suggested_actions=suggestions,
    )
