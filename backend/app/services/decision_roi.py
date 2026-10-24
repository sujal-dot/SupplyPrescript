"""SupplyPrescript — Decision ROI Engine Service (Day 20)
======================================================
Authoritative service calculating financial variances, causal vs predictive savings,
delay differences, transparent Return on Investment (ROI), and multi-dimensional
decision success evaluations from persisted PostgreSQL records.

Mathematical & Accounting Conventions:
--------------------------------------
1. Cost Difference:
   cost_difference = actual_cost - predicted_cost
   - Positive: actual cost exceeded prediction (cost overrun).
   - Negative: actual cost was below prediction (under budget).

2. Money Saved:
   money_saved_vs_prediction = predicted_cost - actual_cost
   - Positive: actual cost was lower than predicted.
   - Negative: overrun.
   - Crucial Distinction: This is variance against forecast, NOT causal proof of savings.

   money_saved_vs_baseline = baseline_cost - actual_cost
   - Calculated ONLY when a documented, verified baseline alternative exists for the
     same shipment, quantity, service tier, and currency.
   - None if baseline is missing or non-comparable.

3. Cost Variance Percentage:
   cost_variance_percentage = ((actual_cost - predicted_cost) / predicted_cost) * 100
   - Returns None if predicted_cost is zero or missing, with explanatory note.

4. Delay Difference:
   delay_difference = actual_delay - predicted_delay
   - Positive: actual delay was worse than predicted.
   - Negative: actual delay was lower (better) than predicted.

5. ROI Percentage:
   net_benefit = baseline_cost - actual_cost - additional_decision_costs
   ROI_percentage = (net_benefit / investment_cost) * 100
   - investment_cost must be a documented, positive amount representing the incremental
     investment or capital outlay dedicated to the decision.
   - Returns UNAVAILABLE if investment_cost is missing, zero, or baseline is absent.
   - Never divides arbitrary savings by predicted cost without documentation.
"""

import math
from collections import defaultdict
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List
from app.services.decision_success import evaluate_decision_success, DecisionSuccessPolicy, DEFAULT_POLICY

CALCULATION_VERSION = "1.0"
CALCULATION_METHOD = (
    "Cost difference = actual_cost - predicted_cost. "
    "Money saved vs prediction = predicted_cost - actual_cost. "
    "Money saved vs baseline = baseline_cost - actual_cost (when baseline exists). "
    "Delay difference = actual_delay - predicted_delay. "
    "ROI = ((baseline_cost - actual_cost - additional_costs) / investment_cost) * 100 "
    "where investment_cost is documented and positive."
)


def compute_baseline_cost(shipment: Any) -> Optional[Decimal]:
    """Calculate documented baseline shipment cost from shipment master record.

    Baseline Cost = (quantity * unit_cost) + shipping_cost
    """
    if not shipment:
        return None

    qty = getattr(shipment, "quantity", None)
    unit_cost = getattr(shipment, "unit_cost", None)
    shipping_cost = getattr(shipment, "shipping_cost", None)

    if qty is not None and unit_cost is not None and shipping_cost is not None:
        try:
            return round((Decimal(str(qty)) * Decimal(str(unit_cost))) + Decimal(str(shipping_cost)), 2)
        except Exception:
            return None
    return None


def calculate_decision_roi(
    decision: Any,
    outcome: Optional[Any] = None,
    shipment: Optional[Any] = None,
    investment_cost_override: Optional[Decimal] = None,
    additional_decision_costs: Optional[Decimal] = None,
    policy: Optional[DecisionSuccessPolicy] = None,
) -> Dict[str, Any]:
    """Compute comprehensive ROI metrics and success evaluation for a single decision.

    Args:
        decision: Decision ORM instance.
        outcome: Outcome ORM instance (optional).
        shipment: Shipment ORM instance (optional).
        investment_cost_override: Explicit incremental investment denominator if documented.
        additional_decision_costs: Additional execution costs (e.g. fees, expedite surcharges).
        policy: Configured DecisionSuccessPolicy for success evaluation.

    Returns:
        Structured dictionary matching DecisionROIResponse schema.
    """
    notes: List[str] = []
    pol = policy or DEFAULT_POLICY

    decision_id_str = (
        getattr(decision, "decision_business_id", None)
        or getattr(decision, "decision_id", None)
        or str(getattr(decision, "id", ""))
    )
    shipment_id_str = getattr(decision, "shipment_id", None) or (
        getattr(shipment, "shipment_id", None) if shipment else None
    )

    # 1. Resolve Persisted Predicted Values (Immutable Snapshot)
    raw_pred_cost = getattr(decision, "predicted_cost", None)
    if raw_pred_cost is None:
        raw_pred_cost = getattr(decision, "estimated_total_cost", None)
    pred_cost: Optional[Decimal] = Decimal(str(raw_pred_cost)) if raw_pred_cost is not None else None

    raw_pred_delay = getattr(decision, "predicted_delay", None)
    if raw_pred_delay is None:
        raw_pred_delay = getattr(decision, "estimated_delay_days", None)
    pred_delay: Optional[Decimal] = Decimal(str(raw_pred_delay)) if raw_pred_delay is not None else None

    decision_currency = (getattr(decision, "currency", None) or "USD").upper()

    # Planned quantity and baseline shipment data
    planned_quantity: Optional[Decimal] = None
    baseline_cost: Optional[Decimal] = None
    if shipment:
        if getattr(shipment, "quantity", None) is not None:
            planned_quantity = Decimal(str(shipment.quantity))
        baseline_cost = compute_baseline_cost(shipment)

    # 2. Resolve Verified Operational Actuals
    act_cost: Optional[Decimal] = None
    act_delay: Optional[Decimal] = None
    act_quantity: Optional[Decimal] = None
    actual_currency: Optional[str] = None
    outcome_recorded = outcome is not None

    if outcome:
        raw_act_cost = getattr(outcome, "actual_cost", None)
        if raw_act_cost is not None:
            act_cost = Decimal(str(raw_act_cost))

        raw_act_delay = getattr(outcome, "actual_delay", None)
        if raw_act_delay is None and getattr(outcome, "actual_delivery_date", None) is not None:
            if getattr(outcome, "actual_delay_days", None) is not None:
                raw_act_delay = getattr(outcome, "actual_delay_days", None)
        if raw_act_delay is not None:
            act_delay = Decimal(str(raw_act_delay))

        raw_act_qty = getattr(outcome, "actual_quantity", None)
        if raw_act_qty is not None:
            act_quantity = Decimal(str(raw_act_qty))

        actual_currency = (getattr(outcome, "currency", None) or decision_currency).upper()
    else:
        notes.append("No operational outcome recorded for this decision; actual metrics are unavailable.")

    # 3. Currency Compatibility Gate
    currency_mismatch = False
    if actual_currency and actual_currency != decision_currency:
        currency_mismatch = True
        notes.append(
            f"Currency mismatch detected: decision is in {decision_currency} while outcome is in {actual_currency}. "
            "Cross-currency variances are blocked to prevent distorted financial calculations."
        )

    # 4. Financial Calculations
    cost_diff: Optional[Decimal] = None
    cost_var_pct: Optional[float] = None
    money_saved_pred: Optional[Decimal] = None
    money_saved_base: Optional[Decimal] = None

    if act_cost is not None and pred_cost is not None:
        if currency_mismatch:
            cost_diff = None
            cost_var_pct = None
            money_saved_pred = None
        else:
            cost_diff = round(act_cost - pred_cost, 2)
            money_saved_pred = round(pred_cost - act_cost, 2)
            if pred_cost > 0:
                cost_var_pct = float(round(((act_cost - pred_cost) / pred_cost) * Decimal("100"), 2))
            else:
                cost_var_pct = None
                notes.append("Predicted cost is zero; cost variance percentage is mathematically undefined.")
    elif act_cost is None:
        notes.append("Actual cost is unavailable; cost variance and savings cannot be calculated.")
    elif pred_cost is None:
        notes.append("Predicted cost was not recorded in the original decision snapshot.")

    # Money Saved vs Baseline
    if baseline_cost is not None and act_cost is not None and not currency_mismatch:
        money_saved_base = round(baseline_cost - act_cost, 2)
    elif baseline_cost is None:
        notes.append("Documented shipment baseline cost is unavailable; baseline savings cannot be verified.")

    # 5. Delay Calculations
    delay_diff: Optional[Decimal] = None
    if act_delay is not None and pred_delay is not None:
        delay_diff = round(act_delay - pred_delay, 2)
    elif act_delay is None:
        notes.append("Actual delay is pending delivery verification.")
    elif pred_delay is None:
        notes.append("Predicted delay was not recorded in original decision.")

    # 6. Return on Investment (ROI) Calculation
    # Determine documented investment cost
    investment_cost: Optional[Decimal] = None
    if investment_cost_override is not None and investment_cost_override > 0:
        investment_cost = investment_cost_override
    elif pred_cost is not None and baseline_cost is not None and pred_cost > baseline_cost:
        # The planned incremental investment over baseline
        investment_cost = round(pred_cost - baseline_cost, 2)

    extra_costs = additional_decision_costs or Decimal("0.0")

    roi_status = "UNAVAILABLE"
    roi_pct: Optional[float] = None
    net_benefit: Optional[Decimal] = None
    roi_reason = ""

    if baseline_cost is None:
        roi_status = "UNAVAILABLE"
        roi_reason = "A valid baseline and investment-cost definition are not available."
    elif act_cost is None:
        roi_status = "UNAVAILABLE"
        roi_reason = "Actual cost is pending; ROI calculation requires verified outcome actuals."
    elif currency_mismatch:
        roi_status = "UNAVAILABLE"
        roi_reason = "Currency mismatch between decision and actual outcome prevents valid ROI calculation."
    elif investment_cost is None or investment_cost <= Decimal("0.0"):
        roi_status = "UNAVAILABLE"
        roi_reason = "A valid baseline and investment-cost definition are not available."
    else:
        # Valid baseline, comparable actuals, positive documented investment denominator
        net_benefit = round(baseline_cost - act_cost - extra_costs, 2)
        roi_pct = float(round((net_benefit / investment_cost) * Decimal("100"), 2))
        roi_status = "CALCULATED"
        roi_reason = (
            f"Calculated as (Net Benefit {net_benefit:,.2f} {decision_currency} / "
            f"Incremental Investment {investment_cost:,.2f} {decision_currency}) * 100."
        )

    # 7. Decision Success Evaluation
    constraint_snapshot = getattr(decision, "constraint_validation_snapshot", None)
    evaluation = evaluate_decision_success(
        predicted_cost=pred_cost if not currency_mismatch else None,
        actual_cost=act_cost if not currency_mismatch else None,
        predicted_delay=pred_delay,
        actual_delay=act_delay,
        planned_quantity=planned_quantity,
        actual_quantity=act_quantity,
        constraint_snapshot=constraint_snapshot,
        policy=pol,
    )

    # Construct formatted payload
    cost_payload = {
        "predicted_cost": f"{pred_cost:.2f}" if pred_cost is not None else None,
        "actual_cost": f"{act_cost:.2f}" if act_cost is not None else None,
        "cost_difference": f"{cost_diff:.2f}" if cost_diff is not None else None,
        "cost_variance_percentage": cost_var_pct,
        "money_saved_vs_prediction": f"{money_saved_pred:.2f}" if money_saved_pred is not None else None,
        "baseline_cost": f"{baseline_cost:.2f}" if baseline_cost is not None else None,
        "money_saved_vs_baseline": f"{money_saved_base:.2f}" if money_saved_base is not None else None,
    }

    delivery_payload = {
        "predicted_delay": float(pred_delay) if pred_delay is not None else None,
        "actual_delay": float(act_delay) if act_delay is not None else None,
        "delay_difference": float(delay_diff) if delay_diff is not None else None,
    }

    roi_payload = {
        "investment_cost": f"{investment_cost:.2f}" if investment_cost is not None else None,
        "net_benefit": f"{net_benefit:.2f}" if net_benefit is not None else None,
        "roi_percentage": roi_pct,
        "status": roi_status,
        "reason": roi_reason,
    }

    return {
        "decision_id": decision_id_str,
        "shipment_id": shipment_id_str,
        "currency": decision_currency,
        "cost": cost_payload,
        "delivery": delivery_payload,
        "roi": roi_payload,
        "decision_evaluation": evaluation,
        "calculation_version": CALCULATION_VERSION,
        "calculation_method": CALCULATION_METHOD,
        "notes": notes,
    }


def compute_portfolio_roi(
    decision_roi_list: List[Dict[str, Any]],
    target_currency: str = "USD",
) -> Dict[str, Any]:
    """Aggregate individual decision ROI calculations into a portfolio summary.

    Enforces:
    - Currency isolation (only aggregates records with matching currency).
    - Exclusion of incomplete/unrecorded records from completed financial totals.
    - True portfolio weighted ROI: sum(net_benefits) / sum(investment_costs) * 100
      (never averages individual percentages!).
    """
    total_decisions = len(decision_roi_list)
    decisions_with_outcomes = 0
    decisions_pending_outcomes = 0
    excluded_incomplete_count = 0

    success_counts: Dict[str, int] = {
        "SUCCESS": 0,
        "PARTIAL_SUCCESS": 0,
        "FAILURE": 0,
        "PENDING_REVIEW": 0,
    }

    total_pred = Decimal("0.0")
    total_act = Decimal("0.0")
    total_baseline_savings = Decimal("0.0")
    has_comparable_cost_records = False
    has_baseline_savings_records = False

    total_net_benefit = Decimal("0.0")
    total_investment_cost = Decimal("0.0")
    has_valid_roi_records = False

    for item in decision_roi_list:
        eval_data = item.get("decision_evaluation", {})
        status = eval_data.get("decision_success", "PENDING_REVIEW")
        success_counts[status] = success_counts.get(status, 0) + 1

        cost_data = item.get("cost", {})
        roi_data = item.get("roi", {})
        curr = item.get("currency", "USD").upper()

        if cost_data.get("actual_cost") is not None:
            decisions_with_outcomes += 1
        else:
            decisions_pending_outcomes += 1

        # Check currency match
        if curr != target_currency.upper():
            excluded_incomplete_count += 1
            continue

        pred_str = cost_data.get("predicted_cost")
        act_str = cost_data.get("actual_cost")

        if pred_str is not None and act_str is not None:
            try:
                p_val = Decimal(str(pred_str))
                a_val = Decimal(str(act_str))
                total_pred += p_val
                total_act += a_val
                has_comparable_cost_records = True
            except Exception:
                excluded_incomplete_count += 1
        else:
            excluded_incomplete_count += 1

        # Baseline savings
        base_saved_str = cost_data.get("money_saved_vs_baseline")
        if base_saved_str is not None:
            try:
                total_baseline_savings += Decimal(str(base_saved_str))
                has_baseline_savings_records = True
            except Exception:
                pass

        # ROI aggregation
        if roi_data.get("status") == "CALCULATED":
            inv_str = roi_data.get("investment_cost")
            net_str = roi_data.get("net_benefit")
            if inv_str is not None and net_str is not None:
                try:
                    inv_dec = Decimal(str(inv_str))
                    net_dec = Decimal(str(net_str))
                    if inv_dec > 0:
                        total_investment_cost += inv_dec
                        total_net_benefit += net_dec
                        has_valid_roi_records = True
                except Exception:
                    pass

    # Aggregated metrics
    agg_cost_var: Optional[Decimal] = None
    agg_cost_var_pct: Optional[float] = None
    agg_money_saved_pred: Optional[Decimal] = None
    if has_comparable_cost_records:
        agg_cost_var = round(total_act - total_pred, 2)
        agg_money_saved_pred = round(total_pred - total_act, 2)
        if total_pred > 0:
            agg_cost_var_pct = float(round(((total_act - total_pred) / total_pred) * Decimal("100"), 2))

    agg_baseline_savings_str: Optional[str] = (
        f"{total_baseline_savings:.2f}" if has_baseline_savings_records else None
    )

    # Aggregate ROI
    if has_valid_roi_records and total_investment_cost > 0:
        agg_roi_pct = float(round((total_net_benefit / total_investment_cost) * Decimal("100"), 2))
        aggregate_roi = {
            "investment_cost": f"{total_investment_cost:.2f}",
            "net_benefit": f"{total_net_benefit:.2f}",
            "roi_percentage": agg_roi_pct,
            "status": "CALCULATED",
            "reason": (
                f"Portfolio ROI weighted across {decisions_with_outcomes} completed decisions: "
                f"(Total Net Benefit {total_net_benefit:,.2f} {target_currency} / "
                f"Total Investment {total_investment_cost:,.2f} {target_currency}) * 100."
            ),
        }
    else:
        aggregate_roi = {
            "investment_cost": None,
            "net_benefit": None,
            "roi_percentage": None,
            "status": "UNAVAILABLE",
            "reason": "Documented baseline and incremental investment denominators are unavailable across completed portfolio decisions.",
        }

    return {
        "total_decisions": total_decisions,
        "decisions_with_outcomes": decisions_with_outcomes,
        "decisions_pending_outcomes": decisions_pending_outcomes,
        "currency": target_currency,
        "total_predicted_cost": f"{total_pred:.2f}" if has_comparable_cost_records else None,
        "total_actual_cost": f"{total_act:.2f}" if has_comparable_cost_records else None,
        "aggregate_cost_variance": f"{agg_cost_var:.2f}" if agg_cost_var is not None else None,
        "aggregate_cost_variance_percentage": agg_cost_var_pct,
        "aggregate_money_saved_vs_prediction": f"{agg_money_saved_pred:.2f}" if agg_money_saved_pred is not None else None,
        "aggregate_baseline_savings": agg_baseline_savings_str,
        "success_counts": success_counts,
        "aggregate_roi": aggregate_roi,
        "excluded_incomplete_records_count": excluded_incomplete_count,
        "calculation_version": CALCULATION_VERSION,
    }


def compute_decision_roi_dashboard(
    evaluated_records: List[Dict[str, Any]],
    target_currency: str = "USD",
    page: int = 1,
    page_size: int = 20,
    active_filters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Compute comprehensive Decision ROI Dashboard metrics (Day 21).

    Enforces:
    - Multi-dimensional success rates with non-distorting denominators (excludes pending reviews).
    - Statistical prediction accuracy (cost MAE, MAPE, RMSE, MSE; delay MAE, MSE).
    - Transparent distinction between forecast variance and verified baseline savings.
    - Full strategy and time-series breakdowns.
    - Zero division safety and currency isolation.
    """
    base_portfolio = compute_portfolio_roi(evaluated_records, target_currency=target_currency)

    total_decisions = base_portfolio["total_decisions"]
    decisions_with_outcomes = base_portfolio["decisions_with_outcomes"]
    decisions_pending_outcomes = base_portfolio["decisions_pending_outcomes"]
    success_counts = base_portfolio["success_counts"]

    successful_count = success_counts.get("SUCCESS", 0)
    partial_count = success_counts.get("PARTIAL_SUCCESS", 0)
    failed_count = success_counts.get("FAILURE", 0)
    pending_count = success_counts.get("PENDING_REVIEW", 0)
    eligible_completed = successful_count + partial_count + failed_count

    success_rate = (
        round((successful_count / eligible_completed) * 100.0, 2)
        if eligible_completed > 0
        else None
    )
    partial_success_rate = (
        round((partial_count / eligible_completed) * 100.0, 2)
        if eligible_completed > 0
        else None
    )
    failure_rate = (
        round((failed_count / eligible_completed) * 100.0, 2)
        if eligible_completed > 0
        else None
    )

    cost_errors: List[float] = []
    cost_abs_errors: List[float] = []
    cost_sq_errors: List[float] = []
    cost_pct_errors: List[float] = []

    delay_errors: List[float] = []
    delay_abs_errors: List[float] = []

    strategy_groups: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "total": 0,
        "completed": 0,
        "successful": 0,
        "partial": 0,
        "failed": 0,
        "pending": 0,
        "cost_diffs": [],
        "pred_costs": [],
        "act_costs": [],
        "baseline_savings": [],
        "investment_costs": [],
        "net_benefits": [],
    })

    timeline_buckets: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "forecast_variance": Decimal("0.0"),
        "baseline_savings": Decimal("0.0"),
        "decision_count": 0,
    })

    valid_cost_comparisons = 0
    valid_delay_comparisons = 0
    valid_baseline_comparisons = 0
    currency_mismatches = 0
    missing_data_count = 0

    performance_items: List[Dict[str, Any]] = []

    for rec in evaluated_records:
        rec_curr = rec.get("currency", "USD").upper()
        if rec_curr != target_currency.upper():
            currency_mismatches += 1

        cost_info = rec.get("cost", {})
        deliv_info = rec.get("delivery", {})
        roi_info = rec.get("roi", {})
        eval_info = rec.get("decision_evaluation", {})

        p_cost_str = cost_info.get("predicted_cost")
        a_cost_str = cost_info.get("actual_cost")
        p_delay = deliv_info.get("predicted_delay")
        a_delay = deliv_info.get("actual_delay")
        base_saved_str = cost_info.get("money_saved_vs_baseline")

        strat = rec.get("strategy") or "UNSPECIFIED"
        strat_stat = strategy_groups[strat]
        strat_stat["total"] += 1

        eval_status = eval_info.get("decision_success", "PENDING_REVIEW")
        if eval_status == "SUCCESS":
            strat_stat["successful"] += 1
        elif eval_status == "PARTIAL_SUCCESS":
            strat_stat["partial"] += 1
        elif eval_status == "FAILURE":
            strat_stat["failed"] += 1
        else:
            strat_stat["pending"] += 1

        if a_cost_str is not None:
            strat_stat["completed"] += 1

        # Accuracy & strategy stats for target currency
        if rec_curr == target_currency.upper():
            if p_cost_str is not None and a_cost_str is not None:
                try:
                    p_val = Decimal(str(p_cost_str))
                    a_val = Decimal(str(a_cost_str))
                    diff = float(a_val - p_val)
                    cost_errors.append(diff)
                    cost_abs_errors.append(abs(diff))
                    cost_sq_errors.append(diff ** 2)
                    if a_val > 0:
                        cost_pct_errors.append((abs(diff) / float(a_val)) * 100.0)

                    strat_stat["cost_diffs"].append(diff)
                    strat_stat["pred_costs"].append(p_val)
                    strat_stat["act_costs"].append(a_val)
                    valid_cost_comparisons += 1
                except Exception:
                    missing_data_count += 1
            else:
                missing_data_count += 1

            if p_delay is not None and a_delay is not None:
                try:
                    d_diff = float(a_delay) - float(p_delay)
                    delay_errors.append(d_diff)
                    delay_abs_errors.append(abs(d_diff))
                    valid_delay_comparisons += 1
                except Exception:
                    pass

            if base_saved_str is not None:
                try:
                    bs_val = Decimal(str(base_saved_str))
                    strat_stat["baseline_savings"].append(bs_val)
                    valid_baseline_comparisons += 1
                except Exception:
                    pass

            if roi_info.get("status") == "CALCULATED":
                inv_str = roi_info.get("investment_cost")
                net_str = roi_info.get("net_benefit")
                if inv_str and net_str:
                    try:
                        strat_stat["investment_costs"].append(Decimal(str(inv_str)))
                        strat_stat["net_benefits"].append(Decimal(str(net_str)))
                    except Exception:
                        pass

        # Savings timeline grouping
        d_time_raw = rec.get("decision_time")
        d_date = "Unknown"
        if d_time_raw:
            try:
                if isinstance(d_time_raw, (datetime, date)):
                    d_date = d_time_raw.strftime("%Y-%m-%d")
                else:
                    d_date = str(d_time_raw)[:10]
            except Exception:
                d_date = "Unknown"

        if rec_curr == target_currency.upper():
            if p_cost_str is not None and a_cost_str is not None:
                try:
                    f_var = Decimal(str(p_cost_str)) - Decimal(str(a_cost_str))
                    timeline_buckets[d_date]["forecast_variance"] += f_var
                except Exception:
                    pass
            if base_saved_str is not None:
                try:
                    timeline_buckets[d_date]["baseline_savings"] += Decimal(str(base_saved_str))
                except Exception:
                    pass
            timeline_buckets[d_date]["decision_count"] += 1

        # Detailed performance record
        perf_item = {
            "decision_id": rec.get("decision_id"),
            "db_id": rec.get("db_id", 0),
            "shipment_id": rec.get("shipment_id"),
            "strategy": rec.get("strategy"),
            "decision_name": rec.get("decision_name") or rec.get("decision"),
            "decision_time": str(d_time_raw) if d_time_raw else None,
            "status": rec.get("status", "RECORDED"),
            "evaluation_status": eval_status,
            "currency": rec_curr,
            "predicted_cost": cost_info.get("predicted_cost"),
            "actual_cost": cost_info.get("actual_cost"),
            "cost_difference": cost_info.get("cost_difference"),
            "cost_variance_pct": cost_info.get("cost_variance_percentage"),
            "predicted_delay": deliv_info.get("predicted_delay"),
            "actual_delay": deliv_info.get("actual_delay"),
            "delay_difference": deliv_info.get("delay_difference"),
            "baseline_savings": cost_info.get("money_saved_vs_baseline"),
            "roi_percentage": roi_info.get("roi_percentage"),
            "roi_status": roi_info.get("status", "UNAVAILABLE"),
        }
        performance_items.append(perf_item)

    # Statistical prediction errors
    cost_mae = round(float(sum(cost_abs_errors) / len(cost_abs_errors)), 2) if cost_abs_errors else None
    cost_mape = round(float(sum(cost_pct_errors) / len(cost_pct_errors)), 2) if cost_pct_errors else None
    cost_rmse = round(float(math.sqrt(sum(cost_sq_errors) / len(cost_sq_errors))), 2) if cost_sq_errors else None
    cost_mean_signed_error = round(float(sum(cost_errors) / len(cost_errors)), 2) if cost_errors else None

    delay_mae_days = round(float(sum(delay_abs_errors) / len(delay_abs_errors)), 2) if delay_abs_errors else None
    delay_mean_error_days = round(float(sum(delay_errors) / len(delay_errors)), 2) if delay_errors else None

    avg_cost_diff_val = round(float(sum(cost_errors) / len(cost_errors)), 2) if cost_errors else None
    avg_cost_diff_str = f"{avg_cost_diff_val:+.2f}" if avg_cost_diff_val is not None else None

    # Strategy breakdowns
    cost_diff_by_strategy: List[Dict[str, Any]] = []
    roi_by_strategy: List[Dict[str, Any]] = []

    for strat_name, s_data in sorted(strategy_groups.items()):
        cnt = len(s_data["cost_diffs"])
        strat_avg_diff = round(sum(s_data["cost_diffs"]) / cnt, 2) if cnt > 0 else None
        strat_pred_sum = sum(s_data["pred_costs"]) if s_data["pred_costs"] else None
        strat_act_sum = sum(s_data["act_costs"]) if s_data["act_costs"] else None

        cost_diff_by_strategy.append({
            "strategy": strat_name,
            "count": cnt,
            "average_cost_difference": f"{strat_avg_diff:+.2f}" if strat_avg_diff is not None else None,
            "total_predicted_cost": f"{strat_pred_sum:.2f}" if strat_pred_sum is not None else None,
            "total_actual_cost": f"{strat_act_sum:.2f}" if strat_act_sum is not None else None,
        })

        strat_eligible = s_data["successful"] + s_data["partial"] + s_data["failed"]
        strat_success_rate = (
            round((s_data["successful"] / strat_eligible) * 100.0, 2)
            if strat_eligible > 0
            else None
        )
        strat_base_saved_sum = sum(s_data["baseline_savings"]) if s_data["baseline_savings"] else None
        strat_inv_sum = sum(s_data["investment_costs"]) if s_data["investment_costs"] else None
        strat_net_sum = sum(s_data["net_benefits"]) if s_data["net_benefits"] else None

        if strat_inv_sum is not None and strat_inv_sum > 0 and strat_net_sum is not None:
            strat_roi_pct = round(float((strat_net_sum / strat_inv_sum) * Decimal("100.0")), 2)
            strat_roi_status = "CALCULATED"
            strat_roi_reason = (
                f"Strategy weighted ROI: ({strat_net_sum:,.2f} {target_currency} net benefit / "
                f"{strat_inv_sum:,.2f} {target_currency} investment) * 100."
            )
        else:
            strat_roi_pct = None
            strat_roi_status = "UNAVAILABLE"
            strat_roi_reason = "Documented incremental investment denominators are unavailable for this strategy."

        roi_by_strategy.append({
            "strategy": strat_name,
            "total_decisions": s_data["total"],
            "completed_decisions": s_data["completed"],
            "successful_decisions": s_data["successful"],
            "success_rate": strat_success_rate,
            "average_cost_difference": f"{strat_avg_diff:+.2f}" if strat_avg_diff is not None else None,
            "verified_baseline_savings": f"{strat_base_saved_sum:.2f}" if strat_base_saved_sum is not None else None,
            "total_investment_cost": f"{strat_inv_sum:.2f}" if strat_inv_sum is not None else None,
            "total_net_benefit": f"{strat_net_sum:.2f}" if strat_net_sum is not None else None,
            "roi_percentage": strat_roi_pct,
            "roi_status": strat_roi_status,
            "roi_reason": strat_roi_reason,
        })

    # Timeline series
    savings_timeline: List[Dict[str, Any]] = []
    cum_forecast_var = Decimal("0.0")
    cum_baseline_saved = Decimal("0.0")

    for dt_str in sorted(timeline_buckets.keys()):
        b_data = timeline_buckets[dt_str]
        cum_forecast_var += b_data["forecast_variance"]
        cum_baseline_saved += b_data["baseline_savings"]

        savings_timeline.append({
            "date": dt_str,
            "forecast_variance": float(round(b_data["forecast_variance"], 2)),
            "cumulative_forecast_variance": float(round(cum_forecast_var, 2)),
            "verified_baseline_savings": float(round(b_data["baseline_savings"], 2)),
            "cumulative_baseline_savings": float(round(cum_baseline_saved, 2)),
            "decision_count": b_data["decision_count"],
        })

    # Pagination for performance table
    total_perf = len(performance_items)
    page_safe = max(1, page)
    page_size_safe = max(1, min(100, page_size))
    total_pages = max(1, math.ceil(total_perf / page_size_safe)) if total_perf > 0 else 1
    start_idx = (page_safe - 1) * page_size_safe
    end_idx = start_idx + page_size_safe
    paged_items = performance_items[start_idx:end_idx]

    performance_page = {
        "items": paged_items,
        "total": total_perf,
        "page": page_safe,
        "page_size": page_size_safe,
        "total_pages": total_pages,
    }

    success_breakdown = [
        {
            "status": "SUCCESS",
            "label": "Successful",
            "count": successful_count,
            "percentage_of_eligible": success_rate,
            "percentage_of_total": round((successful_count / total_decisions) * 100.0, 2) if total_decisions > 0 else 0.0,
            "color": "#10b981",
            "description": "Outcome cost <= +5%, delay <= 0.5 days, and all operational constraints satisfied.",
        },
        {
            "status": "PARTIAL_SUCCESS",
            "label": "Partially Successful",
            "count": partial_count,
            "percentage_of_eligible": partial_success_rate,
            "percentage_of_total": round((partial_count / total_decisions) * 100.0, 2) if total_decisions > 0 else 0.0,
            "color": "#f59e0b",
            "description": "Fulfillable with minor trade-off (cost overrun 5–15% or delay 0.5–2 days) without critical constraint violations.",
        },
        {
            "status": "FAILURE",
            "label": "Failed",
            "count": failed_count,
            "percentage_of_eligible": failure_rate,
            "percentage_of_total": round((failed_count / total_decisions) * 100.0, 2) if total_decisions > 0 else 0.0,
            "color": "#ef4444",
            "description": "Outcome experienced severe cost overrun (>15%), severe delay (>2 days), or hard constraint violation.",
        },
        {
            "status": "PENDING_REVIEW",
            "label": "Pending Review",
            "count": pending_count,
            "percentage_of_eligible": None,
            "percentage_of_total": round((pending_count / total_decisions) * 100.0, 2) if total_decisions > 0 else 0.0,
            "color": "#64748b",
            "description": "Operational execution in progress; actual delivery and cost outcomes have not yet been recorded.",
        },
    ]

    summary_kpis = {
        "total_decisions": total_decisions,
        "completed_decisions": decisions_with_outcomes,
        "pending_decisions": decisions_pending_outcomes,
        "successful_decisions": successful_count,
        "partially_successful_decisions": partial_count,
        "failed_decisions": failed_count,
        "eligible_completed_decisions": eligible_completed,
        "success_rate": success_rate,
        "partial_success_rate": partial_success_rate,
        "failure_rate": failure_rate,
        "average_cost_difference": avg_cost_diff_str,
        "average_cost_variance_percentage": base_portfolio.get("aggregate_cost_variance_percentage"),
        "total_predicted_cost": base_portfolio.get("total_predicted_cost"),
        "total_actual_cost": base_portfolio.get("total_actual_cost"),
        "forecast_variance": base_portfolio.get("aggregate_money_saved_vs_prediction"),
        "verified_baseline_savings": base_portfolio.get("aggregate_baseline_savings"),
        "aggregate_roi": base_portfolio["aggregate_roi"],
        "currency": target_currency,
    }

    data_quality = {
        "total_in_filter": total_decisions,
        "completed_with_valid_costs": valid_cost_comparisons,
        "completed_with_valid_delays": valid_delay_comparisons,
        "decisions_with_valid_baseline": valid_baseline_comparisons,
        "excluded_currency_mismatches": currency_mismatches,
        "excluded_missing_data": missing_data_count + base_portfolio["excluded_incomplete_records_count"],
        "calculation_version": CALCULATION_VERSION,
        "methodology_notes": [
            "Cost difference = actual_cost - predicted_cost (positive = overrun, negative = savings vs forecast).",
            "Success rate denominator strictly excludes pending review decisions to prevent undercounting actual recommendation success.",
            "Verified baseline savings requires a documented, comparable shipment baseline ((quantity * unit_cost) + shipping_cost).",
            "Portfolio ROI is calculated as weighted aggregate net benefit / incremental investment, never as an unweighted average of individual percentages.",
            "Decision success thresholds are provisional and subject to policy tuning by operations management.",
        ],
    }

    result = dict(base_portfolio)
    result.update({
        "filters": active_filters or {},
        "summary": summary_kpis,
        "prediction_accuracy": {
            "cost_mae": cost_mae,
            "cost_mape": cost_mape,
            "cost_rmse": cost_rmse,
            "cost_mean_signed_error": cost_mean_signed_error,
            "cost_records_evaluated": len(cost_abs_errors),
            "delay_mae_days": delay_mae_days,
            "delay_mean_error_days": delay_mean_error_days,
            "delay_records_evaluated": len(delay_abs_errors),
        },
        "success_breakdown": success_breakdown,
        "cost_difference_by_strategy": cost_diff_by_strategy,
        "roi_by_strategy": roi_by_strategy,
        "savings_timeline": savings_timeline,
        "performance_table": performance_page,
        "data_quality": data_quality,
    })
    return result
