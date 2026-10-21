"""
SupplyPrescript — Unit Tests: Prescriptive Decision Ranker (Day 13)
===================================================================
Tests ranking feasible supply-chain alternatives by Day 12 composite objective:
    min Z = C_total + C_delay + C_risk

Verifies:
- Cheapest feasible option wins when delay & risk are comparable.
- A more expensive option can win when documented delay penalties justify it.
- Infeasible/violating options are strictly excluded from recommendation.
- NO_FEASIBLE_OPTION is returned when all alternatives violate constraints.
"""

from __future__ import annotations

import pytest

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
def baseline_summary():
    return BaselineSummary(
        shipment_id="SHIP-001",
        product_id="PROD001",
        product_name="Controller Unit",
        supplier_id="SUP001",
        supplier_name="Alpha Tech",
        transport_mode="Road",
        quantity=100.0,
        unit_cost=50.0,
        shipping_cost=250.0,
        estimated_total_cost=5250.0,
        predicted_delay_probability=0.85,
        predicted_delay_days=8.5,
        risk_level="HIGH",
        planned_lead_time_days=5.0,
        total_delivery_days=13.5,
        currency="USD",
    )


def test_cheapest_feasible_option_wins_when_all_factors_equal(baseline_summary):
    """When risk and delay performance are comparable, the option with lower cost wins."""
    config = get_baseline_scenario()

    opt_a = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=6500.0,
        objective_value=6520.0,
        predicted_delay_days=1.0,
        delay_probability=0.10,
        risk_level=RiskLevel.LOW,
    )
    opt_b = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=5800.0,
        objective_value=5820.0,  # Lower objective value!
        predicted_delay_days=1.0,
        delay_probability=0.10,
        risk_level=RiskLevel.LOW,
    )
    opt_c = AlternativeOption(
        option_id="C",
        name="Delay Product Launch",
        feasibility=FeasibilityStatus.INSUFFICIENT_DATA,
    )

    ranked, winner_id, status, reason, trade_offs = rank_alternatives(
        alternatives=[opt_a, opt_b, opt_c],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "B"
    assert "Option B (Secondary Supplier) is recommended" in reason
    # Check that winner has is_recommended=True and others have False
    winner_opt = next(o for o in ranked if o.option_id == "B")
    assert winner_opt.is_recommended is True
    runner_up = next(o for o in ranked if o.option_id == "A")
    assert runner_up.is_recommended is False


def test_more_expensive_option_can_win_when_delay_penalties_justify_it(baseline_summary):
    """
    Verify that an option with higher direct freight cost can win if its delay penalty is much lower,
    resulting in a lower Day 12 objective cost Z.
    """
    config = get_baseline_scenario()

    # Option A: Freight is $6,000, zero delay -> Z = $6,000
    opt_a = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=6000.0,
        objective_value=6000.0,
        predicted_delay_days=0.0,
        delay_probability=0.05,
        risk_level=RiskLevel.LOW,
    )
    # Option B: Direct cost is $5,500, but predicted delay causes $2,000 in penalties -> Z = $7,500
    opt_b = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=5500.0,
        objective_value=7500.0,  # Higher Z despite lower direct cost!
        predicted_delay_days=4.0,
        delay_probability=0.50,
        risk_level=RiskLevel.MEDIUM,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_a, opt_b],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    # Option A wins because its composite Z is lower!
    assert winner_id == "A"


def test_infeasible_options_are_strictly_excluded_from_recommendation(baseline_summary):
    """Verify that alternatives violating hard constraints cannot be recommended."""
    config = get_baseline_scenario()

    # Option A: Infeasible due to budget violation
    opt_a = AlternativeOption(
        option_id="A",
        name="Air Freight",
        feasibility=FeasibilityStatus.INFEASIBLE,
        estimated_total_cost=55000.0,
        objective_value=55000.0,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Maximum Budget",
                limit_value=50000.0,
                actual_value=55000.0,
                violation_amount=5000.0,
                message="Budget exceeded",
            )
        ],
    )
    # Option B: Feasible but more expensive than Option A's procurement
    opt_b = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.FEASIBLE,
        estimated_total_cost=45000.0,
        objective_value=45000.0,
    )

    ranked, winner_id, status, reason, _ = rank_alternatives(
        alternatives=[opt_a, opt_b],
        baseline=baseline_summary,
        config=config,
    )

    assert status == RecommendationStatus.FEASIBLE_RECOMMENDATION
    assert winner_id == "B"
    # Option A must NOT be recommended
    winner_a = next(o for o in ranked if o.option_id == "A")
    assert winner_a.is_recommended is False


def test_no_feasible_option_returned_when_all_alternatives_infeasible(baseline_summary):
    """Verify that NO_FEASIBLE_OPTION is returned when all candidate options fail constraints."""
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
                message="Exceeds budget limit",
            )
        ],
    )
    opt_b = AlternativeOption(
        option_id="B",
        name="Secondary Supplier",
        feasibility=FeasibilityStatus.INFEASIBLE,
        constraint_violations=[
            ConstraintViolation(
                constraint_name="Supplier Capacity",
                limit_value=50.0,
                actual_value=100.0,
                violation_amount=50.0,
                message="Exceeds supplier capacity",
            )
        ],
    )
    opt_c = AlternativeOption(
        option_id="C",
        name="Delay Product Launch",
        feasibility=FeasibilityStatus.INSUFFICIENT_DATA,
    )

    ranked, winner_id, status, reason, trade_offs = rank_alternatives(
        alternatives=[opt_a, opt_b, opt_c],
        baseline=baseline_summary,
        config=config,
    )

    assert winner_id is None
    assert status == RecommendationStatus.NO_FEASIBLE_OPTION
    assert "NO_FEASIBLE_OPTION" in reason
    assert all(o.is_recommended is False for o in ranked)
    assert "No candidate alternative satisfies all hard business constraints" in trade_offs
