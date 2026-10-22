"""SupplyPrescript — Closed-Loop Outcome Comparison Engine (Day 19)
==================================================================
Compares prescriptive optimization predictions recorded at decision execution time
against verified operational actuals retrieved from PostgreSQL.

Calculates:
- Cost variance (actual_cost - predicted_cost)
- Cost variance percentage ((actual_cost - predicted_cost) / predicted_cost * 100)
- Delivery date variance (actual_delivery_date - predicted_delivery_date in days)
- Delay variance (actual_delay - predicted_delay in days)
- Quantity variance (actual_quantity - planned_quantity)

Enforces:
- Strict sign conventions (positive cost variance = over budget; positive delay variance = later than predicted)
- Currency consistency (rejects or marks mismatched currencies as undefined)
- Zero-division safety on percentage calculation
- Explicit null handling for missing or unfinalized actual values (never coerced to zero)
- Immutable prediction snapshots (predictions are read from stored decision records, never re-optimized)
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, Any


def compute_outcome_comparison(
    decision: Any,
    outcome: Optional[Any] = None,
    shipment: Optional[Any] = None,
) -> Dict[str, Any]:
    """Compute complete predicted vs actual outcome comparison.

    Args:
        decision: Decision ORM instance with stored predicted values.
        outcome: Outcome ORM instance (optional, if recorded).
        shipment: Shipment ORM instance (optional, for planned baselines).

    Returns:
        Structured dictionary matching OutcomeComparisonResponse schema.
    """
    decision_id_str = getattr(decision, "decision_business_id", None) or getattr(decision, "decision_id", None) or str(getattr(decision, "id", ""))
    shipment_id_str = getattr(decision, "shipment_id", None) or (getattr(shipment, "shipment_id", None) if shipment else None)

    # 1. Resolve Stored Predictions
    raw_pred_cost = getattr(decision, "predicted_cost", None)
    if raw_pred_cost is None:
        raw_pred_cost = getattr(decision, "estimated_total_cost", None)
    pred_cost = Decimal(str(raw_pred_cost)) if raw_pred_cost is not None else None

    raw_pred_delay = getattr(decision, "predicted_delay", None)
    pred_delay = Decimal(str(raw_pred_delay)) if raw_pred_delay is not None else None

    pred_currency = getattr(decision, "currency", None) or "USD"

    # Planned quantity and planned supplier from shipment
    planned_quantity = None
    planned_supplier = None
    baseline_delivery_date = None
    if shipment:
        if getattr(shipment, "quantity", None) is not None:
            planned_quantity = Decimal(str(shipment.quantity))
        planned_supplier = getattr(shipment, "supplier_id", None)
        baseline_delivery_date = getattr(shipment, "expected_delivery_date", None)

    # Predicted delivery date = baseline expected date + predicted delay days
    predicted_delivery_date: Optional[date] = None
    if baseline_delivery_date:
        if pred_delay is not None:
            delay_days_int = int(round(float(pred_delay)))
            predicted_delivery_date = baseline_delivery_date + timedelta(days=delay_days_int)
        else:
            predicted_delivery_date = baseline_delivery_date

    predicted_payload = {
        "predicted_cost": float(pred_cost) if pred_cost is not None else None,
        "predicted_delay": float(pred_delay) if pred_delay is not None else None,
        "predicted_delivery_date": predicted_delivery_date.isoformat() if predicted_delivery_date else None,
        "planned_quantity": float(planned_quantity) if planned_quantity is not None else None,
        "planned_supplier": planned_supplier,
        "currency": pred_currency,
    }

    # 2. Check if an Outcome Exists
    if outcome is None:
        return {
            "decision_id": decision_id_str,
            "shipment_id": shipment_id_str,
            "predicted": predicted_payload,
            "actual": None,
            "variance": None,
            "data_completeness": "NO_OUTCOME",
            "notes": ["No operational outcome has been recorded yet for this decision."],
        }

    # 3. Resolve Operational Actuals
    raw_act_cost = getattr(outcome, "actual_cost", None)
    act_cost = Decimal(str(raw_act_cost)) if raw_act_cost is not None else None

    act_delivery_date = getattr(outcome, "actual_delivery_date", None)
    if isinstance(act_delivery_date, datetime):
        act_delivery_date = act_delivery_date.date()

    raw_act_delay = getattr(outcome, "actual_delay", None)
    # Only fall back to legacy actual_delay_days if actual_delivery_date exists (undelivered must remain None)
    if raw_act_delay is None and act_delivery_date is not None and getattr(outcome, "actual_delay_days", None) is not None:
        raw_act_delay = getattr(outcome, "actual_delay_days", None)
    act_delay = Decimal(str(raw_act_delay)) if raw_act_delay is not None else None

    raw_act_qty = getattr(outcome, "actual_quantity", None)
    act_quantity = Decimal(str(raw_act_qty)) if raw_act_qty is not None else None

    act_supplier = getattr(outcome, "actual_supplier", None)
    act_currency = getattr(outcome, "currency", None) or "USD"
    outcome_status = getattr(outcome, "outcome_status", "RECORDED")
    outcome_source = getattr(outcome, "source", "manual_entry")

    actual_payload = {
        "outcome_id": getattr(outcome, "outcome_id", None),
        "actual_cost": float(act_cost) if act_cost is not None else None,
        "actual_delay": float(act_delay) if act_delay is not None else None,
        "actual_delivery_date": act_delivery_date.isoformat() if act_delivery_date else None,
        "actual_quantity": float(act_quantity) if act_quantity is not None else None,
        "actual_supplier": act_supplier,
        "currency": act_currency,
        "outcome_status": outcome_status,
        "source": outcome_source,
        "recorded_at": getattr(outcome, "recorded_at", None).isoformat() if getattr(outcome, "recorded_at", None) else None,
    }

    # 4. Calculate Variances & Handle Boundary Cases
    notes = []
    cost_variance: Optional[float] = None
    cost_variance_pct: Optional[float] = None
    delay_variance: Optional[float] = None
    delivery_date_variance_days: Optional[int] = None
    quantity_variance: Optional[float] = None
    supplier_matched: Optional[bool] = None

    # Cost Variance calculation
    if act_cost is not None and pred_cost is not None:
        if act_currency.upper() != pred_currency.upper():
            notes.append(f"Currency mismatch: predicted {pred_currency} vs actual {act_currency}. Cost variance skipped.")
        else:
            diff_cost = act_cost - pred_cost
            cost_variance = float(diff_cost)
            if pred_cost > 0:
                cost_variance_pct = float(round((diff_cost / pred_cost) * Decimal("100"), 2))
            else:
                notes.append("Predicted cost is zero; cost variance percentage is mathematically undefined.")
    elif act_cost is None:
        notes.append("Actual cost not provided.")
    elif pred_cost is None:
        notes.append("Predicted cost not recorded in original decision.")

    # Delay Variance calculation
    if act_delay is not None and pred_delay is not None:
        delay_variance = float(round(act_delay - pred_delay, 2))
    elif act_delay is None:
        notes.append("Actual delay is pending or shipment is undelivered.")
    elif pred_delay is None:
        notes.append("Predicted delay not recorded in original decision.")

    # Delivery Date Variance calculation (in calendar days)
    if act_delivery_date is not None and predicted_delivery_date is not None:
        delivery_date_variance_days = (act_delivery_date - predicted_delivery_date).days
    elif act_delivery_date is None:
        notes.append("Actual delivery date is not yet recorded.")
    elif predicted_delivery_date is None:
        notes.append("Baseline expected delivery date is unavailable on shipment.")

    # Quantity Variance calculation
    if act_quantity is not None and planned_quantity is not None:
        quantity_variance = float(round(act_quantity - planned_quantity, 2))
    elif act_quantity is None:
        notes.append("Actual quantity not recorded.")

    # Supplier comparison
    if act_supplier and planned_supplier:
        supplier_matched = (act_supplier.strip().upper() == planned_supplier.strip().upper())

    variance_payload = {
        "cost_variance": cost_variance,
        "cost_variance_percentage": cost_variance_pct,
        "delay_variance": delay_variance,
        "delivery_date_variance_days": delivery_date_variance_days,
        "quantity_variance": quantity_variance,
        "supplier_matched": supplier_matched,
    }

    # 5. Determine Completeness
    all_metrics = [cost_variance, delay_variance, delivery_date_variance_days, quantity_variance]
    if all(m is not None for m in all_metrics):
        completeness = "COMPLETE"
    elif any(m is not None for m in all_metrics):
        completeness = "PARTIAL"
    else:
        completeness = "NO_OUTCOME"

    return {
        "decision_id": decision_id_str,
        "shipment_id": shipment_id_str,
        "predicted": predicted_payload,
        "actual": actual_payload,
        "variance": variance_payload,
        "data_completeness": completeness,
        "notes": notes,
    }
