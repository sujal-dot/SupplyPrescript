"""
SupplyPrescript — Hard Constraint Audit Suite: Recommendation Safety Gate (Day 15)
==================================================================================
Audits recommendation safety gating: ensures no unverified, infeasible,
or constraint-violating candidate is ever presented as a recommended action.
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
    RiskLevel,
    SolutionValidationReport,
)


@pytest.fixture
def baseline():
    return BaselineSummary(
        shipment_id="TEST-SAFETY-01",
        product_id="PROD001",
        product_name="Component",
        supplier_id="SUP001",
        supplier_name="Alpha",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=200.0,
        estimated_total_cost=5200.0,
        predicted_delay_probability=0.80,
        predicted_delay_days=8.0,
        risk_level="HIGH",
        planned_lead_time_days=4.0,
        total_delivery_days=12.0,
        currency="USD",
    )


def test_safety_gate_strictly_excludes_infeasible_candidate(baseline):
    """Verify that an infeasible option is excluded from recommendation."""
    config = get_baseline_scenario()

    opt_infeasible = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=70000.0,  # Exceeds budget
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=50000.0,
                actual_value=70000.0,
                violation_amount=20000.0,
                message="Exceeds budget limit",
            )
        ],
    )
    opt_feasible = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=30000.0,
        objective_value=30000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_infeasible, opt_feasible],
        baseline=baseline,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "B"
    assert next(o for o in ranked if o.option_id == "A").is_recommended is False


def test_safety_gate_fails_closed_when_all_ineligible(baseline):
    """Verify that fail-closed NO_FEASIBLE_OPTION is returned when no alternative passes safety gate."""
    config = get_baseline_scenario()

    opt_a = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.INFEASIBLE,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=50000.0,
                actual_value=60000.0,
                violation_amount=10000.0,
                message="Budget exceeded",
            )
        ],
    )
    opt_b = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.ERROR,
        explanation="Vendor database offline",
    )
    opt_c = AlternativeOption(
        option_id="C",
        name="Delay Product Launch",
        feasibility=FeasibilityStatus.INSUFFICIENT_DATA,
    )

    ranked, winner_id, status, reason, trade_offs = rank_alternatives(
        alternatives=[opt_a, opt_b, opt_c],
        baseline=baseline,
        config=config,
    )

    assert winner_id is None
    assert status == RecommendationStatus.NO_FEASIBLE_OPTION
    assert "NO_FEASIBLE_OPTION" in reason
    assert all(o.is_recommended is False for o in ranked)
