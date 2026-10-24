"""SupplyPrescript — Unit Tests for Decision ROI Engine (Day 20)
==============================================================
Validates:
1. Predicted cost $15,000 and actual cost $18,000 produce a $3,000 overrun.
2. Cost variance percentage is calculated correctly (20.0%).
3. Actual cost below prediction produces positive money_saved_vs_prediction.
4. Actual cost above prediction produces negative money_saved_vs_prediction.
5. Predicted delay of 3 days and actual delay of 2 days produces a delay difference of -1 day.
6. Zero predicted cost does not cause division by zero.
7. Missing actual cost produces unavailable cost-dependent metrics.
8. Missing actual delay produces unavailable delay-dependent metrics.
9. Missing or incompatible currency prevents invalid financial comparisons.
10. Missing baseline prevents unsupported claims of verified savings.
11. Missing investment cost produces unavailable ROI.
12. A valid baseline and investment definition produce the expected ROI.
13. A decision that exceeds predicted cost but meets its delivery target is evaluated per policy.
14. A hard-constraint failure is surfaced in the decision evaluation.
15. Quantity variance uses compatible units.
16. Incomplete outcomes are not classified as fully successful.
"""

from decimal import Decimal
from types import SimpleNamespace
import pytest

from app.services.decision_roi import calculate_decision_roi, compute_portfolio_roi
from app.services.decision_success import (
    evaluate_decision_success,
    DecisionSuccessPolicy,
)


def test_cost_overrun_and_variance_percentage():
    """Requirement 1 & 2: Predicted $15,000, Actual $18,000 -> $3,000 overrun (+20.0%)."""
    decision = SimpleNamespace(
        decision_id="DEC-001",
        predicted_cost=Decimal("15000.00"),
        predicted_delay=Decimal("3.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("18000.00"),
        actual_delay=Decimal("3.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["cost_difference"] == "3000.00"
    assert result["cost"]["cost_variance_percentage"] == 20.0
    assert result["cost"]["money_saved_vs_prediction"] == "-3000.00"


def test_cost_savings_vs_prediction_positive():
    """Requirement 3: Actual cost below prediction produces positive money_saved_vs_prediction."""
    decision = SimpleNamespace(
        decision_id="DEC-002",
        predicted_cost=Decimal("15000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("13500.00"),
        actual_delay=Decimal("2.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["cost_difference"] == "-1500.00"
    assert result["cost"]["money_saved_vs_prediction"] == "1500.00"
    assert result["cost"]["cost_variance_percentage"] == -10.0


def test_cost_savings_vs_prediction_negative_on_overrun():
    """Requirement 4: Actual cost above prediction produces negative money_saved_vs_prediction."""
    decision = SimpleNamespace(
        decision_id="DEC-003",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("1.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("12500.00"),
        actual_delay=Decimal("1.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["money_saved_vs_prediction"] == "-2500.00"
    assert result["cost"]["cost_difference"] == "2500.00"


def test_delay_difference_calculation():
    """Requirement 5: Predicted delay 3 days, actual delay 2 days -> delay difference -1 day."""
    decision = SimpleNamespace(
        decision_id="DEC-004",
        predicted_cost=Decimal("5000.00"),
        predicted_delay=Decimal("3.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("5000.00"),
        actual_delay=Decimal("2.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["delivery"]["predicted_delay"] == 3.0
    assert result["delivery"]["actual_delay"] == 2.0
    assert result["delivery"]["delay_difference"] == -1.0


def test_zero_predicted_cost_handles_zero_division():
    """Requirement 6: Zero predicted cost does not cause division by zero."""
    decision = SimpleNamespace(
        decision_id="DEC-005",
        predicted_cost=Decimal("0.00"),
        predicted_delay=Decimal("1.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("500.00"),
        actual_delay=Decimal("1.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["cost_variance_percentage"] is None
    assert any("zero" in note.lower() for note in result["notes"])


def test_missing_actual_cost_produces_unavailable_metrics():
    """Requirement 7: Missing actual cost produces unavailable cost-dependent metrics."""
    decision = SimpleNamespace(
        decision_id="DEC-006",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    # Outcome exists but actual_cost is None
    outcome = SimpleNamespace(
        actual_cost=None,
        actual_delay=Decimal("2.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["actual_cost"] is None
    assert result["cost"]["cost_difference"] is None
    assert result["cost"]["cost_variance_percentage"] is None
    assert result["cost"]["money_saved_vs_prediction"] is None
    assert result["cost"]["money_saved_vs_baseline"] is None
    assert result["roi"]["status"] == "UNAVAILABLE"


def test_missing_actual_delay_produces_unavailable_delay_metrics():
    """Requirement 8: Missing actual delay produces unavailable delay-dependent metrics."""
    decision = SimpleNamespace(
        decision_id="DEC-007",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("9500.00"),
        actual_delay=None,
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["delivery"]["actual_delay"] is None
    assert result["delivery"]["delay_difference"] is None
    assert result["decision_evaluation"]["delivery_performance"] == "UNKNOWN"
    assert result["decision_evaluation"]["data_completeness"] == "PARTIAL"


def test_incompatible_currency_blocks_financial_comparisons():
    """Requirement 9: Incompatible currency prevents invalid financial comparisons."""
    decision = SimpleNamespace(
        decision_id="DEC-008",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("12000.00"),
        actual_delay=Decimal("2.0"),
        currency="EUR",  # Mismatch
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    assert result["cost"]["cost_difference"] is None
    assert result["cost"]["cost_variance_percentage"] is None
    assert result["cost"]["money_saved_vs_prediction"] is None
    assert result["roi"]["status"] == "UNAVAILABLE"
    assert any("currency mismatch" in n.lower() for n in result["notes"])


def test_missing_baseline_prevents_unsupported_savings_claims():
    """Requirement 10: Missing baseline prevents unsupported claims of verified savings."""
    decision = SimpleNamespace(
        decision_id="DEC-009",
        predicted_cost=Decimal("15000.00"),
        predicted_delay=Decimal("3.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("12000.00"),
        actual_delay=Decimal("2.0"),
        currency="USD",
    )
    # No shipment passed -> baseline is None
    result = calculate_decision_roi(decision=decision, outcome=outcome, shipment=None)

    assert result["cost"]["baseline_cost"] is None
    assert result["cost"]["money_saved_vs_baseline"] is None
    # Still provides comparison vs prediction
    assert result["cost"]["money_saved_vs_prediction"] == "3000.00"


def test_missing_investment_cost_produces_unavailable_roi():
    """Requirement 11: Missing investment cost produces unavailable ROI."""
    shipment = SimpleNamespace(
        quantity=100,
        unit_cost=Decimal("100.00"),
        shipping_cost=Decimal("500.00"),  # Baseline = 10,500.00
    )
    decision = SimpleNamespace(
        decision_id="DEC-010",
        predicted_cost=Decimal("10500.00"),  # Same as baseline -> incremental investment = 0
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("9000.00"),
        actual_delay=Decimal("1.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome, shipment=shipment)

    assert result["roi"]["status"] == "UNAVAILABLE"
    assert result["roi"]["roi_percentage"] is None
    assert "investment-cost definition are not available" in result["roi"]["reason"]


def test_valid_baseline_and_investment_calculates_roi():
    """Requirement 12: A valid baseline and investment definition produce the expected ROI."""
    # Baseline: 100 units * $100 + $500 shipping = $10,500.00
    shipment = SimpleNamespace(
        quantity=100,
        unit_cost=Decimal("100.00"),
        shipping_cost=Decimal("500.00"),
    )
    # Option A expedited predicted cost = $13,500.00 -> planned incremental investment = $3,000.00
    decision = SimpleNamespace(
        decision_id="DEC-011",
        predicted_cost=Decimal("13500.00"),
        predicted_delay=Decimal("1.0"),
        currency="USD",
    )
    # Actual cost = $11,000.00 -> Net Benefit = Baseline ($10,500) - Actual ($11,000) = -$500
    # Wait, let's test a scenario where actual cost achieves verified savings or explicit investment:
    # Say baseline was $20,000, actual cost was $16,000 -> Net Benefit = $4,000
    # Investment cost override = $2,000 -> ROI = (4000 / 2000) * 100 = 200.0%
    shipment2 = SimpleNamespace(
        quantity=200,
        unit_cost=Decimal("95.00"),
        shipping_cost=Decimal("1000.00"),  # Baseline = 20,000.00
    )
    decision2 = SimpleNamespace(
        decision_id="DEC-011B",
        predicted_cost=Decimal("22000.00"),  # Planned investment = 2,000
        predicted_delay=Decimal("1.0"),
        currency="USD",
    )
    outcome2 = SimpleNamespace(
        actual_cost=Decimal("16000.00"),
        actual_delay=Decimal("1.0"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision2, outcome=outcome2, shipment=shipment2)

    assert result["cost"]["baseline_cost"] == "20000.00"
    assert result["cost"]["money_saved_vs_baseline"] == "4000.00"
    assert result["roi"]["status"] == "CALCULATED"
    assert result["roi"]["investment_cost"] == "2000.00"
    assert result["roi"]["net_benefit"] == "4000.00"
    assert result["roi"]["roi_percentage"] == 200.0


def test_cost_overrun_with_delivery_target_met_evaluates_correctly():
    """Requirement 13: Decision exceeding predicted cost but meeting delivery target is evaluated per policy."""
    decision = SimpleNamespace(
        decision_id="DEC-012",
        predicted_cost=Decimal("15000.00"),
        predicted_delay=Decimal("3.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("18000.00"),  # Cost overrun
        actual_delay=Decimal("2.0"),      # Delivery earlier than predicted!
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    eval_data = result["decision_evaluation"]
    assert eval_data["cost_performance"] == "WORSE_THAN_PREDICTED"
    assert eval_data["delivery_performance"] == "BETTER_THAN_PREDICTED"
    assert eval_data["decision_success"] == "PARTIAL_SUCCESS"
    assert "Cost exceeded prediction while delivery was earlier than predicted" in eval_data["success_reason"]


def test_hard_constraint_failure_surfaced():
    """Requirement 14: A hard-constraint failure is surfaced in the decision evaluation."""
    decision = SimpleNamespace(
        decision_id="DEC-013",
        predicted_cost=Decimal("15000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
        constraint_validation_snapshot={
            "budget": "FAIL",
            "capacity": "PASS",
        },
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("14000.00"),
        actual_delay=Decimal("1.5"),
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome)

    eval_data = result["decision_evaluation"]
    assert eval_data["constraint_compliance"] == "FAIL"
    assert eval_data["decision_success"] == "FAILURE"
    assert "Mandatory business constraint violation detected: budget failed." in eval_data["success_reason"]


def test_quantity_variance_and_fulfillment():
    """Requirement 15: Quantity variance uses compatible units and evaluates target."""
    shipment = SimpleNamespace(
        quantity=500,
        unit_cost=Decimal("10.00"),
        shipping_cost=Decimal("100.00"),
    )
    decision = SimpleNamespace(
        decision_id="DEC-014",
        predicted_cost=Decimal("5100.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    outcome = SimpleNamespace(
        actual_cost=Decimal("5100.00"),
        actual_delay=Decimal("2.0"),
        actual_quantity=Decimal("450"),  # 50 units short
        currency="USD",
    )

    result = calculate_decision_roi(decision=decision, outcome=outcome, shipment=shipment)

    eval_data = result["decision_evaluation"]
    assert eval_data["quantity_performance"] == "PARTIAL_FULFILLMENT"
    assert eval_data["decision_success"] == "PARTIAL_SUCCESS"


def test_incomplete_outcome_not_classified_as_fully_successful():
    """Requirement 16: Incomplete outcomes are not classified as fully successful."""
    decision = SimpleNamespace(
        decision_id="DEC-015",
        predicted_cost=Decimal("10000.00"),
        predicted_delay=Decimal("2.0"),
        currency="USD",
    )
    # No outcome recorded at all
    result = calculate_decision_roi(decision=decision, outcome=None)

    eval_data = result["decision_evaluation"]
    assert eval_data["decision_success"] == "PENDING_REVIEW"
    assert eval_data["data_completeness"] == "INSUFFICIENT"
    assert eval_data["cost_performance"] == "UNKNOWN"
    assert eval_data["delivery_performance"] == "UNKNOWN"


def test_portfolio_roi_aggregation_weights_correctly():
    """Portfolio ROI calculation aggregates net benefits and investments without averaging percentages."""
    # Decision 1: Investment 2000, Net Benefit 4000 (ROI 200%)
    # Decision 2: Investment 8000, Net Benefit 4000 (ROI 50%)
    # Average of percentages would be (200 + 50)/2 = 125%
    # Proper portfolio ROI is (4000 + 4000) / (2000 + 8000) * 100 = 8000 / 10000 * 100 = 80.0%
    d1 = {
        "currency": "USD",
        "cost": {"predicted_cost": "12000.00", "actual_cost": "8000.00", "money_saved_vs_baseline": "4000.00"},
        "delivery": {"predicted_delay": 2.0, "actual_delay": 2.0, "delay_difference": 0.0},
        "roi": {"status": "CALCULATED", "investment_cost": "2000.00", "net_benefit": "4000.00", "roi_percentage": 200.0},
        "decision_evaluation": {"decision_success": "SUCCESS"},
    }
    d2 = {
        "currency": "USD",
        "cost": {"predicted_cost": "18000.00", "actual_cost": "14000.00", "money_saved_vs_baseline": "4000.00"},
        "delivery": {"predicted_delay": 3.0, "actual_delay": 2.5, "delay_difference": -0.5},
        "roi": {"status": "CALCULATED", "investment_cost": "8000.00", "net_benefit": "4000.00", "roi_percentage": 50.0},
        "decision_evaluation": {"decision_success": "SUCCESS"},
    }
    # Decision 3: Incomplete / pending
    d3 = {
        "currency": "USD",
        "cost": {"predicted_cost": "5000.00", "actual_cost": None},
        "delivery": {"predicted_delay": 1.0, "actual_delay": None},
        "roi": {"status": "UNAVAILABLE", "investment_cost": None, "net_benefit": None, "roi_percentage": None},
        "decision_evaluation": {"decision_success": "PENDING_REVIEW"},
    }

    portfolio = compute_portfolio_roi([d1, d2, d3], target_currency="USD")

    assert portfolio["total_decisions"] == 3
    assert portfolio["decisions_with_outcomes"] == 2
    assert portfolio["decisions_pending_outcomes"] == 1
    assert portfolio["excluded_incomplete_records_count"] == 1
    assert portfolio["total_predicted_cost"] == "30000.00"
    assert portfolio["total_actual_cost"] == "22000.00"
    assert portfolio["aggregate_cost_variance"] == "-8000.00"
    assert portfolio["aggregate_baseline_savings"] == "8000.00"
    assert portfolio["aggregate_roi"]["status"] == "CALCULATED"
    assert portfolio["aggregate_roi"]["roi_percentage"] == 80.0
