"""
SupplyPrescript — Unit Tests: Prescriptive Decision Alternatives (Day 13)
========================================================================
Verifies deterministic generation of the three alternative decisions:
- Option A: Air Freight
- Option B: Secondary Supplier
- Option C: Delay Product Launch
"""

from __future__ import annotations

import pytest

from optimization.alternatives import (
    build_baseline_summary,
    generate_alternatives_for_shipment,
    generate_option_a_air_freight,
    generate_option_b_secondary_supplier,
    generate_option_c_delay_launch,
)
from optimization.config import ScenarioConfig, get_baseline_scenario
from optimization.decision_schemas import FeasibilityStatus, RiskLevel


@pytest.fixture
def sample_shipment_payload():
    """Deterministic synthetic test fixture representing an at-risk shipment."""
    return {
        "shipment_id": "TEST-SHIP-001",
        "supplier_id": "SUP001",
        "supplier_name": "Alpha Manufacturing",
        "product_id": "PROD001",
        "product_name": "Industrial Micro-Controller",
        "origin": "Mumbai",
        "destination": "Delhi",
        "quantity": 100,
        "unit_cost": 50.0,
        "shipping_cost": 250.0,
        "lead_time": 5.0,
        "delay_days": 8.0,
        "delay_probability": 0.85,
        "predicted_delay_days": 8.0,
        "supplier_reliability": 0.82,
        "inventory_level": 80,
        "demand": 120,
        "transport_mode": "Road",
        "season": "Winter",
        "priority": "High",
    }


@pytest.fixture
def sample_candidate_suppliers():
    """Synthetic secondary supplier fixture."""
    return [
        {
            "supplier_id": "SUP002",
            "supplier_name": "Beta Electro-Hub",
            "capacity": 3000.0,
            "base_lead_time": 4.0,
            "supplier_reliability": 0.92,
            "origin": "Bengaluru",
            "unit_cost": 52.0,
        }
    ]


def test_baseline_summary_construction(sample_shipment_payload):
    """Test that baseline summary accurately derives procurement, shipping, and delivery metrics."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    assert baseline.shipment_id == "TEST-SHIP-001"
    assert baseline.quantity == 100.0
    assert baseline.unit_cost == 50.0
    assert baseline.shipping_cost == 250.0
    # Total cost = 100 * 50 + 250 = 5250
    assert baseline.estimated_total_cost == 5250.0
    assert baseline.planned_lead_time_days == 5.0
    assert baseline.total_delivery_days == 13.0  # 5 + 8


def test_option_a_air_freight_does_not_hardcode_cost(sample_shipment_payload):
    """Verify Option A calculates air freight dynamically from route distance and rate, not $15,000."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    opt_a = generate_option_a_air_freight(sample_shipment_payload, baseline, config)

    assert opt_a.option_id == "A"
    assert opt_a.transport_mode == "Air"
    # Must NOT equal hardcoded illustrative $15,000
    assert opt_a.additional_cost != 15000.0
    assert opt_a.additional_cost > 0.0
    assert opt_a.estimated_total_cost > baseline.estimated_total_cost
    # Lead time should be accelerated (nominal 0.4x)
    assert opt_a.estimated_delivery_days < baseline.total_delivery_days
    assert opt_a.feasibility in (FeasibilityStatus.FEASIBLE, FeasibilityStatus.INFEASIBLE)


def test_option_b_secondary_supplier_cost_delta(sample_shipment_payload, sample_candidate_suppliers):
    """Verify Option B calculates cost difference Delta C_B and percentage change mathematically."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    opt_b = generate_option_b_secondary_supplier(
        shipment=sample_shipment_payload,
        baseline=baseline,
        config=config,
        candidate_suppliers=sample_candidate_suppliers,
    )

    assert opt_b.option_id == "B"
    assert opt_b.supplier_id == "SUP002"
    assert opt_b.supplier_name == "Beta Electro-Hub"
    assert opt_b.feasibility == FeasibilityStatus.FEASIBLE

    # Mathematical identity: additional_cost = C_B - C_baseline
    expected_delta = round(opt_b.estimated_total_cost - baseline.estimated_total_cost, 2)
    assert opt_b.additional_cost == pytest.approx(expected_delta, abs=1e-2)

    # % Delta = Delta / C_baseline * 100
    expected_pct = round((expected_delta / baseline.estimated_total_cost) * 100.0, 2)
    assert opt_b.additional_cost_percentage == pytest.approx(expected_pct, abs=1e-2)
    # Must NOT equal hardcoded +10.0%
    assert opt_b.additional_cost_percentage != 10.0


def test_option_b_insufficient_data_when_no_supplier_exists(sample_shipment_payload):
    """Verify Option B returns INSUFFICIENT_DATA when no qualified secondary supplier exists."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    opt_b = generate_option_b_secondary_supplier(
        shipment=sample_shipment_payload,
        baseline=baseline,
        config=config,
        candidate_suppliers=[],  # Empty candidate pool
        db=None,
    )

    assert opt_b.option_id == "B"
    assert opt_b.feasibility == FeasibilityStatus.INSUFFICIENT_DATA
    assert opt_b.estimated_total_cost is None
    assert "No qualified secondary supplier was found" in opt_b.explanation


def test_option_c_delay_launch_insufficient_data_without_config(sample_shipment_payload):
    """Verify Option C returns INSUFFICIENT_DATA when launch commercial penalty data is unconfigured."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    # Payload with no launch delay financial penalty configured
    opt_c = generate_option_c_delay_launch(sample_shipment_payload, baseline, config)

    assert opt_c.option_id == "C"
    assert opt_c.feasibility == FeasibilityStatus.INSUFFICIENT_DATA
    assert opt_c.additional_cost == 0.0  # Zero direct freight delta
    assert opt_c.schedule_impact_days == baseline.predicted_delay_days
    assert "monetary commercial impact is unknown" in opt_c.explanation


def test_option_c_delay_launch_with_configured_daily_cost(sample_shipment_payload):
    """Verify Option C computes launch penalty when launch_delay_cost_per_day is provided."""
    config = get_baseline_scenario()
    baseline = build_baseline_summary(sample_shipment_payload, config)

    shipment_with_penalty = dict(sample_shipment_payload, launch_delay_cost_per_day=500.0)
    opt_c = generate_option_c_delay_launch(shipment_with_penalty, baseline, config)

    # 8.0 days * $500/day = $4,000 penalty
    assert opt_c.additional_cost == 4000.0
    assert opt_c.estimated_total_cost == (baseline.estimated_total_cost + 4000.0)


def test_generate_all_three_alternatives_pipeline(sample_shipment_payload, sample_candidate_suppliers):
    """Test generating all three alternatives in a single execution."""
    config = get_baseline_scenario()
    baseline, alternatives, warnings = generate_alternatives_for_shipment(
        shipment=sample_shipment_payload,
        config=config,
        candidate_suppliers=sample_candidate_suppliers,
    )

    assert len(alternatives) == 3
    option_ids = [opt.option_id for opt in alternatives]
    assert option_ids == ["A", "B", "C"]
    assert isinstance(warnings, list)


def test_empty_shipment_raises_value_error():
    """Verify passing empty shipment dictionary raises ValueError."""
    config = get_baseline_scenario()
    with pytest.raises(ValueError, match="must not be empty"):
        generate_alternatives_for_shipment({}, config)
