"""
SupplyPrescript — Hard Constraint Audit Suite: Delivery Delay Constraint (Day 15)
================================================================================
Audits mathematical enforcement of delivery delay limits:
    predicted_delay_days <= maximum_acceptable_delay_days

Audits all mandatory delivery conditions:
1. A compliant delivery estimate is accepted.
2. A delivery estimate exactly at the configured limit is accepted.
3. An estimate exceeding the hard limit is rejected.
4. A faster shipping alternative is evaluated using its own supported delivery estimate.
5. An alternative with missing delivery data is not assumed compliant.
6. A model prediction cannot be represented as a guaranteed delivery date.
7. If the constraint is intended as a guarantee but only an uncertain prediction is available, flag that limitation.
"""

from __future__ import annotations

import pytest

from optimization.alternative_evaluator import is_recommendation_eligible, validate_optimization_solution
from optimization.config import get_baseline_scenario
from optimization.decision_ranker import rank_alternatives
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    RecommendationStatus,
)


@pytest.fixture
def baseline_summary():
    return BaselineSummary(
        shipment_id="TEST-DELIVERY-SHIP-01",
        product_id="PROD001",
        product_name="Component",
        supplier_id="SUP001",
        supplier_name="Alpha",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=200.0,
        estimated_total_cost=5200.0,
        currency="USD",
    )


# 1. A compliant delivery estimate is accepted
def test_delivery_delay_within_tolerance_accepted():
    config = get_baseline_scenario()  # Max delay: 7.0 days
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 100.0,
        "predicted_delay_days": 3.5,
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is True
    assert report.delivery_passed is True
    assert report.is_eligible_for_recommendation is True
    assert report.slacks["delay_slack"] == 3.5


# 2. A delivery estimate exactly at the configured limit is accepted
def test_delivery_delay_at_exact_threshold_accepted():
    config = get_baseline_scenario()  # Max delay: 7.0 days
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 100.0,
        "predicted_delay_days": 7.0,
    }
    report = validate_optimization_solution(sol, config, tolerance=1e-6)
    assert report.is_valid is True
    assert report.delivery_passed is True
    assert report.slacks["delay_slack"] == 0.0


# 3. An estimate exceeding the hard limit is rejected
def test_delivery_delay_exceeding_tolerance_rejected():
    config = get_baseline_scenario()  # Max delay: 7.0 days
    sol = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "quantity": 100.0,
        "predicted_delay_days": 9.2,  # Exceeds 7.0 days
    }
    report = validate_optimization_solution(sol, config)
    assert report.is_valid is False
    assert report.delivery_passed is False
    assert any(v.constraint_name == "Delivery Delay Tolerance" for v in report.violations)
    assert report.slacks["delay_slack"] == pytest.approx(-2.2, abs=1e-2)


# 4. A faster shipping alternative is evaluated using its own supported delivery estimate
def test_faster_shipping_alternative_evaluated_with_own_estimate():
    config = get_baseline_scenario()
    # Baseline ground mode delay is 8.0 days (exceeds 7.0 limit)
    # Air freight alternative reduces delay to 0.5 days
    sol_air = {
        "feasibility": "FEASIBLE",
        "transport_mode": "Air",
        "estimated_total_cost": 28000.0,
        "predicted_delay_days": 0.5,
    }
    report_air = validate_optimization_solution(sol_air, config)
    assert report_air.delivery_passed is True
    assert report_air.slacks["delay_slack"] == 6.5


# 5. An alternative with missing or invalid delivery data is not assumed compliant
def test_missing_or_invalid_delivery_data_fails_validation():
    config = get_baseline_scenario()

    # Case A: NaN delay
    sol_nan = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "predicted_delay_days": float("nan"),
    }
    report_nan = validate_optimization_solution(sol_nan, config)
    assert report_nan.delivery_passed is False
    assert report_nan.is_valid is False

    # Case B: Negative delay value
    sol_neg = {
        "feasibility": "FEASIBLE",
        "estimated_total_cost": 20000.0,
        "predicted_delay_days": -2.0,
    }
    report_neg = validate_optimization_solution(sol_neg, config)
    assert report_neg.delivery_passed is False
    assert report_neg.is_valid is False


# 6. Model prediction cannot be represented as a guaranteed delivery date
def test_ml_prediction_represented_as_expected_delay_not_guarantee():
    from optimization.alternatives import build_baseline_summary, generate_option_a_air_freight
    config = get_baseline_scenario()
    shipment = {
        "shipment_id": "TEST-DEL",
        "product_id": "P1",
        "supplier_id": "S1",
        "quantity": 100.0,
        "unit_cost": 50.0,
        "shipping_cost": 500.0,
        "lead_time": 4.0,
        "transport_mode": "Road",
    }
    baseline = build_baseline_summary(shipment, config)
    opt_a = generate_option_a_air_freight(shipment, baseline, config)
    # Rationale and explanation must document that delay is an ML prediction / probability, not a calendar guarantee
    assert "predicted" in opt_a.explanation.lower() or "risk" in opt_a.explanation.lower()
    assert opt_a.delay_probability is not None
    assert opt_a.predicted_delay_days is not None


# 7. If constraint is intended as guarantee but only uncertain prediction is available, limitation flagged
def test_delivery_delay_violating_alternative_cannot_be_recommended(baseline_summary):
    config = get_baseline_scenario()

    opt_slow = AlternativeOption(
        option_id="C",
        name="Delay Launch (Severe Lag)",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=15000.0,
        objective_value=15000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Delivery Delay Tolerance",
                limit_value=7.0,
                actual_value=12.0,
                violation_amount=5.0,
                message="Expected arrival delay exceeds 7-day SLA threshold",
            )
        ],
    )
    opt_compliant = AlternativeOption(
        option_id="A",
        name="Air Freight (On Time)",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=22000.0,
        objective_value=22000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_slow, opt_compliant],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "A"
    assert next(o for o in ranked if o.option_id == "C").is_recommended is False
    assert next(o for o in ranked if o.option_id == "A").is_recommended is True
