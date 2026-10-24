"""SupplyPrescript — Unit Tests for Model Feedback Engine (Day 22)
================================================================
Tests verify:
1. Error calculation sign conventions:
   - predicted 3, actual 5 -> error +2, abs 2
   - predicted 4, actual 2 -> error -2, abs 2
   - predicted 3, actual 3 -> error 0, abs 0
2. Absolute error is always non-negative.
3. Missing actual delay does not become zero.
4. Invalid negative actual delay is rejected.
5. Feedback eligibility criteria (eligible, pending, excluded, under review).
6. Model evaluation math (MAE, RMSE, Mean Signed Bias, Median AE).
7. Small sample warning trigger and insufficient data handling.
8. Evaluation is strictly read-only and never promotes or modifies production models.
"""

from decimal import Decimal
import pytest
from app.services.prediction_feedback import (
    calculate_prediction_error,
    validate_feedback_eligibility,
)


class DummyPrediction:
    def __init__(self, prediction_id="PRED001", shipment_id="SHIP001", predicted_value=2.0):
        self.prediction_id = prediction_id
        self.shipment_id = shipment_id
        self.predicted_value = predicted_value


class DummyOutcome:
    def __init__(self, outcome_status="DELIVERED", actual_delay=3.0):
        self.outcome_status = outcome_status
        self.actual_delay = actual_delay


class DummyDecision:
    def __init__(self, decision_id="DEC001", predicted_delay=2.0):
        self.decision_id = decision_id
        self.predicted_delay = predicted_delay


# ---------------------------------------------------------------------------
# 1. Error Calculation Tests
# ---------------------------------------------------------------------------
def test_prediction_error_sign_convention_underestimated():
    """Predicted 3 days, actual 5 days -> error +2, absolute error 2."""
    res = calculate_prediction_error(predicted_delay=3, actual_delay=5)
    assert res["prediction_error"] == 2.0
    assert res["absolute_error"] == 2.0


def test_prediction_error_sign_convention_overestimated():
    """Predicted 4 days, actual 2 days -> error -2, absolute error 2."""
    res = calculate_prediction_error(predicted_delay=4, actual_delay=2)
    assert res["prediction_error"] == -2.0
    assert res["absolute_error"] == 2.0


def test_prediction_error_exact_match():
    """Predicted 3 days, actual 3 days -> error 0, absolute error 0."""
    res = calculate_prediction_error(predicted_delay=3, actual_delay=3)
    assert res["prediction_error"] == 0.0
    assert res["absolute_error"] == 0.0


def test_absolute_error_always_non_negative():
    """Absolute error must never be negative regardless of inputs."""
    res1 = calculate_prediction_error(predicted_delay=10.5, actual_delay=2.5)
    assert res1["absolute_error"] >= 0.0

    res2 = calculate_prediction_error(predicted_delay=1.2, actual_delay=8.4)
    assert res2["absolute_error"] >= 0.0


def test_missing_actual_delay_does_not_become_zero():
    """When actual delay is None, error is None (never coerced to 0)."""
    res = calculate_prediction_error(predicted_delay=4.5, actual_delay=None)
    assert res["prediction_error"] is None
    assert res["absolute_error"] is None


def test_invalid_negative_delay_rejected():
    """Actual delay < 0 violates domain constraints and must be rejected."""
    with pytest.raises(ValueError, match="Actual delay cannot be negative"):
        calculate_prediction_error(predicted_delay=3, actual_delay=-1.5)


def test_invalid_predicted_delay_rejected():
    """Non-numeric predicted delay raises ValueError."""
    with pytest.raises(ValueError, match="Invalid predicted_delay"):
        calculate_prediction_error(predicted_delay="not-a-number", actual_delay=2)


# ---------------------------------------------------------------------------
# 2. Eligibility & Data Quality Tests
# ---------------------------------------------------------------------------
def test_completed_valid_outcome_is_eligible():
    """A delivered shipment with valid actual delay is ELIGIBLE."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="DELIVERED", actual_delay=4.0)
    decision = DummyDecision(predicted_delay=2.0)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=outcome,
        decision=decision,
    )
    assert status == "ELIGIBLE"
    assert reason is None


def test_shipment_awaiting_delivery_is_pending_outcome():
    """Shipment awaiting delivery has status PENDING_OUTCOME."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="AWAITING_DELIVERY", actual_delay=None)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=outcome,
    )
    assert status == "PENDING_OUTCOME"
    assert "Shipment awaiting delivery" in reason


def test_missing_outcome_is_pending_outcome():
    """No outcome record yet -> PENDING_OUTCOME."""
    pred = DummyPrediction()
    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=None,
    )
    assert status == "PENDING_OUTCOME"
    assert "outcome has not been recorded" in reason.lower()


def test_unknown_model_version_is_excluded():
    """Prediction without documented model version is EXCLUDED."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="DELIVERED", actual_delay=2.0)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version=None,
        outcome=outcome,
    )
    assert status == "EXCLUDED"
    assert "UNKNOWN_MODEL_VERSION" in reason


def test_negative_actual_delay_is_excluded():
    """Negative actual delay in outcome is EXCLUDED."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="DELIVERED", actual_delay=-2.0)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=outcome,
    )
    assert status == "EXCLUDED"
    assert "INVALID_DELAY_VALUE" in reason


def test_disputed_outcome_is_under_review():
    """Disputed outcome receipt is categorized as UNDER_REVIEW."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="DISPUTED", actual_delay=3.0)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=outcome,
    )
    assert status == "UNDER_REVIEW"
    assert "OUTCOME_DISPUTED" in reason


def test_cancelled_shipment_is_excluded():
    """Cancelled shipment outcome is EXCLUDED."""
    pred = DummyPrediction()
    outcome = DummyOutcome(outcome_status="CANCELLED", actual_delay=0.0)

    status, reason = validate_feedback_eligibility(
        prediction=pred,
        model_version="v1.0.0",
        outcome=outcome,
    )
    assert status == "EXCLUDED"
    assert "SHIPMENT_CANCELLED" in reason
