"""SupplyPrescript — Decision Success Evaluation Engine (Day 20)
==============================================================
Multi-dimensional decision success evaluator. Evaluates cost performance, delivery
performance, hard-constraint compliance, quantity fulfillment, and data completeness
independently under a configurable, explainable evaluation policy.
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Dict, Any, Tuple


@dataclass
class DecisionSuccessPolicy:
    """Configurable decision success evaluation policy.

    Attributes:
        cost_tolerance_pct: Percentage tolerance for cost equivalence (default: 0.0%).
        delay_tolerance_days: Days tolerance for delivery delay equivalence (default: 0.0).
        quantity_tolerance_pct: Percentage tolerance for quantity fulfillment (default: 0.0%).
        primary_objective: Evaluation trade-off priority: 'BALANCED', 'DELIVERY', or 'COST'.
        is_provisional: Flag indicating that default thresholds are provisional.
    """
    cost_tolerance_pct: float = 0.0
    delay_tolerance_days: float = 0.0
    quantity_tolerance_pct: float = 0.0
    primary_objective: str = "BALANCED"
    is_provisional: bool = True


DEFAULT_POLICY = DecisionSuccessPolicy()


def evaluate_decision_success(
    predicted_cost: Optional[Decimal],
    actual_cost: Optional[Decimal],
    predicted_delay: Optional[Decimal],
    actual_delay: Optional[Decimal],
    planned_quantity: Optional[Decimal] = None,
    actual_quantity: Optional[Decimal] = None,
    constraint_snapshot: Optional[Dict[str, Any]] = None,
    policy: Optional[DecisionSuccessPolicy] = None,
) -> Dict[str, Any]:
    """Evaluate decision outcome success across independent dimensions.

    Args:
        predicted_cost: Original predicted cost.
        actual_cost: Verified operational actual cost.
        predicted_delay: Original predicted delay in days.
        actual_delay: Verified operational delay in days.
        planned_quantity: Documented planned shipment quantity.
        actual_quantity: Verified operational actual quantity delivered.
        constraint_snapshot: Dict of constraint verification results (e.g. {"budget": "PASS"}).
        policy: Configured DecisionSuccessPolicy (defaults to DEFAULT_POLICY).

    Returns:
        Structured evaluation dictionary conforming to DecisionEvaluation schema.
    """
    pol = policy or DEFAULT_POLICY

    # 1. Data Completeness Assessment
    # Rule: Missing required fields must produce UNKNOWN or PENDING_REVIEW, not assumed pass.
    has_cost = actual_cost is not None and predicted_cost is not None
    has_delay = actual_delay is not None and predicted_delay is not None
    has_quantity = actual_quantity is not None and planned_quantity is not None

    if has_cost and has_delay:
        completeness = "COMPLETE" if (has_quantity or planned_quantity is None) else "PARTIAL"
    elif has_cost or has_delay:
        completeness = "PARTIAL"
    else:
        completeness = "INSUFFICIENT"

    # 2. Cost Performance Dimension
    cost_perf = "UNKNOWN"
    if has_cost and predicted_cost is not None and actual_cost is not None:
        cost_diff = actual_cost - predicted_cost
        tolerance_amt = (
            abs(predicted_cost) * Decimal(str(pol.cost_tolerance_pct / 100.0))
            if pol.cost_tolerance_pct > 0
            else Decimal("0.0")
        )

        if cost_diff < -tolerance_amt:
            cost_perf = "BETTER_THAN_PREDICTED"
        elif abs(cost_diff) <= tolerance_amt:
            cost_perf = "ON_TARGET"
        else:
            cost_perf = "WORSE_THAN_PREDICTED"

    # 3. Delivery Performance Dimension
    delivery_perf = "UNKNOWN"
    if has_delay and predicted_delay is not None and actual_delay is not None:
        delay_diff = actual_delay - predicted_delay
        tolerance_days = Decimal(str(pol.delay_tolerance_days))

        if delay_diff < -tolerance_days:
            delivery_perf = "BETTER_THAN_PREDICTED"
        elif abs(delay_diff) <= tolerance_days:
            delivery_perf = "ON_TARGET"
        else:
            delivery_perf = "WORSE_THAN_PREDICTED"

    # 4. Hard Constraint Compliance Dimension
    # Check stored constraint snapshot
    constraint_compliance = "PASS"
    failed_constraints = []
    if constraint_snapshot and isinstance(constraint_snapshot, dict):
        for c_name, c_status in constraint_snapshot.items():
            if str(c_status).upper() == "FAIL":
                constraint_compliance = "FAIL"
                failed_constraints.append(c_name)
    elif not constraint_snapshot:
        constraint_compliance = "UNKNOWN"

    # 5. Quantity Fulfillment Dimension
    quantity_perf = "UNKNOWN"
    if has_quantity and planned_quantity is not None and actual_quantity is not None:
        qty_diff = actual_quantity - planned_quantity
        qty_tolerance = (
            planned_quantity * Decimal(str(pol.quantity_tolerance_pct / 100.0))
            if pol.quantity_tolerance_pct > 0
            else Decimal("0.0")
        )

        if qty_diff > qty_tolerance:
            quantity_perf = "EXCEEDED_TARGET"
        elif abs(qty_diff) <= qty_tolerance:
            quantity_perf = "MET_TARGET"
        elif actual_quantity > 0:
            quantity_perf = "PARTIAL_FULFILLMENT"
        else:
            quantity_perf = "BELOW_TARGET"

    # 6. Overall Decision Success Synthesis
    # Rules:
    # - If data is INSUFFICIENT -> PENDING_REVIEW
    # - If constraint failure -> FAILURE
    # - If data is PARTIAL -> PENDING_REVIEW
    # - If both cost and delivery on target / better -> SUCCESS
    # - If trade-off (one better/on target, one worse) -> PARTIAL_SUCCESS (or per primary objective)
    # - If both worse -> FAILURE

    decision_success = "PENDING_REVIEW"
    reasons = []

    if completeness == "INSUFFICIENT":
        decision_success = "PENDING_REVIEW"
        reasons.append("Insufficient outcome data: actual cost and delivery outcomes are not yet recorded.")
    elif constraint_compliance == "FAIL":
        decision_success = "FAILURE"
        reasons.append(
            f"Mandatory business constraint violation detected: {', '.join(failed_constraints)} failed."
        )
    elif completeness == "PARTIAL":
        decision_success = "PENDING_REVIEW"
        if has_cost and not has_delay:
            reasons.append(f"Cost evaluated as {cost_perf.replace('_', ' ').lower()}, but delivery outcome is pending.")
        elif has_delay and not has_cost:
            reasons.append(f"Delivery evaluated as {delivery_perf.replace('_', ' ').lower()}, but actual cost is unverified.")
        else:
            reasons.append("Partial outcome recorded; complete evaluation requires finalized delivery and financial records.")
    else:
        # We have both cost and delivery actuals
        cost_ok = cost_perf in ("BETTER_THAN_PREDICTED", "ON_TARGET")
        deliv_ok = delivery_perf in ("BETTER_THAN_PREDICTED", "ON_TARGET")

        if cost_ok and deliv_ok:
            if quantity_perf in ("BELOW_TARGET", "PARTIAL_FULFILLMENT"):
                decision_success = "PARTIAL_SUCCESS"
                reasons.append("Cost and delivery targets achieved, but quantity fulfillment was below target.")
            else:
                decision_success = "SUCCESS"
                reasons.append("Decision met or exceeded all cost and delivery expectations without constraint violations.")
        elif not cost_ok and deliv_ok:
            # Cost overrun, but delivery target met
            if pol.primary_objective == "DELIVERY":
                decision_success = "SUCCESS"
                reasons.append("Delivery target achieved under delivery-priority policy despite cost exceeding prediction.")
            else:
                decision_success = "PARTIAL_SUCCESS"
                reasons.append(
                    "Cost exceeded prediction while delivery was earlier than predicted or on target; critical schedule milestone met."
                )
        elif cost_ok and not deliv_ok:
            # Cost under/on target, but delivery delayed
            if pol.primary_objective == "COST":
                decision_success = "SUCCESS"
                reasons.append("Cost targets achieved under cost-priority policy despite delivery delay exceeding prediction.")
            else:
                decision_success = "PARTIAL_SUCCESS"
                reasons.append(
                    "Actual cost was within or below prediction, but delivery delay exceeded forecast."
                )
        else:
            # Both cost and delivery failed
            decision_success = "FAILURE"
            reasons.append("Both actual cost and delivery delay exceeded predictions, failing operational objectives.")

    success_reason = " ".join(reasons)

    return {
        "decision_success": decision_success,
        "cost_performance": cost_perf,
        "delivery_performance": delivery_perf,
        "constraint_compliance": constraint_compliance,
        "quantity_performance": quantity_perf,
        "data_completeness": completeness,
        "success_reason": success_reason,
        "policy_is_provisional": pol.is_provisional,
    }
