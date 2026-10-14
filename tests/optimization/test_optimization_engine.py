"""
Optimization Engine Integration Test Forwarder (Phase 4 / Day 11)
=================================================================
Runs the optimization module unit test suite as part of the unified test pipeline.
"""

from optimization.config import load_scenario_config
from optimization.problem import solve_optimization_problem
from optimization.variables import CandidateOption, ProductData


def test_optimization_integration_pipeline():
    """Verify that the prescriptive optimization problem solves end-to-end."""
    config = load_scenario_config()
    products = [
        ProductData(
            product_id="P1",
            product_name="Benchmark Product",
            starting_inventory=50.0,
            demand=120.0,
            unit_cost=30.0,
            holding_cost_per_unit=1.5,
            shortage_penalty_per_unit=45.0,
        )
    ]
    candidate_options = [
        CandidateOption(
            supplier_id="S1",
            supplier_name="Benchmark Supplier",
            product_id="P1",
            product_name="Benchmark Product",
            transport_mode="Road",
            unit_cost=30.0,
            shipping_cost_per_unit=2.0,
            lead_time_days=3.0,
            predicted_delay_probability=0.10,
            predicted_delay_days=0.5,
            expected_delay_cost_per_unit=0.01,
            supplier_capacity=2000.0,
        )
    ]

    result = solve_optimization_problem(candidate_options, products, config)
    assert result.status == "OPTIMAL"
    assert result.is_optimal() is True
    assert result.objective.total_cost is not None
    assert len(result.decisions) == 1
    assert result.decisions[0].quantity == 1070.0  # demand 120 + min_inv 1000 - start 50 = 1070
