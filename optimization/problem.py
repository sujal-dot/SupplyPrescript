"""
SupplyPrescript — Prescriptive Optimization Problem Factory & Solver
====================================================================
Core optimization orchestration layer. Constructs mathematical programming models,
applies variables, objectives, and constraints, executes solvers, and assembles
structured audit results.

CLI Entrypoint:
    python -m optimization.problem
"""

from __future__ import annotations

import logging
import sys
import time
from typing import Any, Dict, List, Optional, Tuple

import pulp

from optimization.config import ScenarioConfig, load_scenario_config
from optimization.constraints import (
    AppliedConstraint,
    ConstraintRegistry,
    apply_business_constraints,
)
from optimization.objective import ObjectiveExpressions, build_objective
from optimization.results import (
    ConstraintCheckResult,
    ConstraintSummary,
    DecisionAllocation,
    InfeasibilityReport,
    InventoryResult,
    ObjectiveSummary,
    OptimizationResult,
    SupplierCapacityUtilization,
)
from optimization.validation import (
    PreSolveValidationReport,
    diagnose_infeasibility,
    validate_optimization_inputs,
)
from optimization.variables import (
    CandidateOption,
    OptimizationVariables,
    ProductData,
    create_decision_variables,
)

logger = logging.getLogger("optimization.problem")


from optimization.solver import (
    build_optimization_problem,
    enrich_candidate_options_with_ml,
    solve_optimization_problem,
    solve_supply_chain,
)


# ---------------------------------------------------------------------------
# Database & ML Integration Data Loader
# ---------------------------------------------------------------------------
def load_optimization_data_from_db(
    db: Any,
    config: ScenarioConfig,
    max_suppliers: int = 15,
    max_products: int = 10,
) -> Tuple[List[CandidateOption], List[ProductData]]:
    """
    Query real PostgreSQL database records (Suppliers, Products, Inventory, Shipments)
    and evaluate active ML prediction models (v1.0 XGBoost) to construct candidate
    options and product data.
    """
    from sqlalchemy import func
    from app.models.inventory import Inventory
    from app.models.product import Product
    from app.models.shipment import Shipment
    from app.models.supplier import Supplier
    from ml.feature_config import calculate_hub_distance_km
    from ml.predict import predict_shipment

    logger.info("Loading real database records for optimization problem.")

    # 1. Fetch Products
    db_products = db.query(Product).order_by(Product.id.asc()).limit(max_products).all()
    if not db_products:
        raise ValueError("No products found in database.")

    products: List[ProductData] = []
    prod_ids = [p.product_id for p in db_products]

    for p in db_products:
        # Latest inventory level and demand
        latest_inv = (
            db.query(Inventory)
            .filter(Inventory.product_id == p.product_id)
            .order_by(Inventory.inventory_date.desc())
            .first()
        )
        starting_inv = float(latest_inv.inventory_level) if (latest_inv and latest_inv.inventory_level is not None) else 100.0
        demand_val = float(latest_inv.demand) if (latest_inv and latest_inv.demand is not None) else (float(p.base_demand) if p.base_demand else 150.0)

        u_cost = float(p.unit_cost) if p.unit_cost else 50.0
        h_cost = round(u_cost * config.inventory.holding_cost_rate, 4)
        short_penalty = round(u_cost * config.inventory.shortage_penalty_rate, 4)

        products.append(
            ProductData(
                product_id=p.product_id,
                product_name=p.product_name,
                starting_inventory=starting_inv,
                demand=demand_val,
                unit_cost=u_cost,
                holding_cost_per_unit=h_cost,
                shortage_penalty_per_unit=short_penalty,
                minimum_inventory=0.0,
            )
        )

    # 2. Fetch Suppliers
    db_suppliers = db.query(Supplier).order_by(Supplier.id.asc()).limit(max_suppliers).all()
    if not db_suppliers:
        raise ValueError("No suppliers found in database.")

    candidate_options: List[CandidateOption] = []
    modes = ["Road", "Air", "Rail"]

    for s in db_suppliers:
        s_cap = float(s.capacity) if (s.capacity and s.capacity > 0) else config.supplier.default_max_capacity_units
        base_lead = float(s.base_lead_time) if (s.base_lead_time and s.base_lead_time > 0) else 5.0
        rel = float(s.supplier_reliability) if s.supplier_reliability else 0.85
        origin_city = str(s.origin).strip().title() if s.origin else "Mumbai"
        dest_city = "Delhi"
        dist_km = float(calculate_hub_distance_km(origin_city, dest_city))

        # Query historical average delay for supplier
        hist_avg_delay = (
            db.query(func.avg(Shipment.delay_days))
            .filter(Shipment.supplier_id == s.supplier_id)
            .scalar()
        )
        hist_delay_val = float(hist_avg_delay) if hist_avg_delay is not None else 1.0

        for p in products:
            for mode in modes:
                # Mode-specific lead time adjustment
                mode_lead_mult = {"Air": 0.4, "Road": 1.0, "Rail": 1.4, "Sea": 2.2}.get(mode, 1.0)
                lead_time = max(1.0, round(base_lead * mode_lead_mult, 1))

                # Mode-specific shipping cost per unit
                mode_cost_rate = {"Air": 0.35, "Road": 0.08, "Rail": 0.04, "Sea": 0.02}.get(mode, 0.08)
                shipping_cost_per_unit = round(max(5.0, (dist_km * mode_cost_rate / 100.0)), 2)

                # ML Inference: score delay risk using registered models
                feature_dict = {
                    "supplier_reliability": rel,
                    "historical_avg_delay": hist_delay_val,
                    "lead_time": lead_time,
                    "inventory_level": p.starting_inventory,
                    "demand": p.demand,
                    "quantity": 100,  # Reference evaluation batch
                    "shipping_cost": shipping_cost_per_unit * 100,
                    "distance": dist_km,
                    "transport_mode": mode,
                    "season": "Post-Monsoon",
                    "priority": "Medium",
                }

                try:
                    pred = predict_shipment(feature_dict)
                    prob = float(pred.get("delay_probability", 0.20))
                    pred_days = float(pred.get("predicted_delay_days", 1.0))
                except Exception as ml_exc:
                    logger.debug("ML inference fallback for (%s, %s): %s", s.supplier_id, mode, ml_exc)
                    prob = 0.20
                    pred_days = 1.0

                # Expected delay cost per unit
                # Cost = P(delay) * (daily_delay_penalty * predicted_delay_days / 100)
                expected_delay_cost = round(
                    prob * (config.delivery.daily_delay_penalty * pred_days / 100.0),
                    4,
                )

                candidate_options.append(
                    CandidateOption(
                        supplier_id=s.supplier_id,
                        supplier_name=s.supplier_name,
                        product_id=p.product_id,
                        product_name=p.product_name,
                        transport_mode=mode,
                        unit_cost=p.unit_cost,
                        shipping_cost_per_unit=shipping_cost_per_unit,
                        lead_time_days=lead_time,
                        predicted_delay_probability=round(prob, 4),
                        predicted_delay_days=round(pred_days, 2),
                        expected_delay_cost_per_unit=expected_delay_cost,
                        supplier_capacity=s_cap,
                        origin=origin_city,
                        destination=dest_city,
                        distance_km=dist_km,
                    )
                )

    logger.info("Constructed %d candidate options across %d products and %d suppliers.", len(candidate_options), len(products), len(db_suppliers))
    return candidate_options, products


# ---------------------------------------------------------------------------
# CLI Execution Entrypoint
# ---------------------------------------------------------------------------
def main() -> None:
    """CLI execution entrypoint: python -m optimization.problem"""
    print("=" * 80)
    print(" SupplyPrescript — Prescriptive Supply Chain Optimization Engine")
    print("=" * 80)

    config = load_scenario_config()
    print(f"\nScenario: {config.scenario_name}")
    print(f"Budget Limit: {config.budget.max_total_cost:,.2f} {config.budget.currency}")
    print(f"Minimum Inventory Target: {config.inventory.minimum_required_units:,.1f} units")
    print(f"Maximum Acceptable Delay: {config.delivery.maximum_acceptable_delay_days:.1f} days")
    print(f"Solver Engine: {config.optimization.solver} (Timeout: {config.optimization.time_limit_seconds}s)")

    # Attempt loading from PostgreSQL
    try:
        from app.database.connection import SessionLocal
        db = SessionLocal()
        candidate_options, products = load_optimization_data_from_db(db, config, max_suppliers=10, max_products=5)
        db.close()
        print(f"\n[INFO] Loaded real database records: {len(products)} products, {len(candidate_options)} candidate options.")
    except Exception as db_exc:
        print(f"\n[INFO] Live DB session unavailable ({db_exc}). Generating deterministic test fixture.")
        # Deterministic benchmark fixture
        products = [
            ProductData("PROD001", "STM32 Microcontroller IC", starting_inventory=230, demand=350, unit_cost=45.0, holding_cost_per_unit=2.25, shortage_penalty_per_unit=67.5),
            ProductData("PROD002", "High-Voltage Power Supply 24V", starting_inventory=260, demand=400, unit_cost=125.0, holding_cost_per_unit=6.25, shortage_penalty_per_unit=187.5),
        ]
        candidate_options = [
            CandidateOption("SUP001", "Apex Micro Electronics", "PROD001", "STM32 Microcontroller IC", "Road", 45.0, 3.5, 5.0, 0.15, 0.8, 0.03, 5000.0),
            CandidateOption("SUP001", "Apex Micro Electronics", "PROD001", "STM32 Microcontroller IC", "Air", 45.0, 12.0, 2.0, 0.05, 0.2, 0.01, 5000.0),
            CandidateOption("SUP002", "Havells Industrial Components", "PROD002", "High-Voltage Power Supply 24V", "Road", 125.0, 8.0, 3.0, 0.22, 1.2, 0.07, 4000.0),
            CandidateOption("SUP002", "Havells Industrial Components", "PROD002", "High-Voltage Power Supply 24V", "Rail", 125.0, 4.0, 6.0, 0.35, 2.5, 0.22, 4000.0),
        ]

    print("\nExecuting Prescriptive Optimization Solver...")
    result = solve_optimization_problem(candidate_options, products, config)

    print("\n" + "-" * 80)
    print(f"Status: {result.status} (Solver: {result.solver_name}, Time: {result.solve_time_seconds:.4f}s)")
    if result.objective.total_cost is not None:
        print(f"Total Modeled Cost: {result.objective.total_cost:,.2f} {result.objective.currency}")
        if result.objective.cost_breakdown:
            print("Cost Breakdown:")
            for comp, cost in result.objective.cost_breakdown.items():
                print(f"  - {comp.replace('_', ' ').title()}: {cost:,.2f} {result.objective.currency}")
    if result.budget_utilization_pct is not None:
        print(f"Budget Utilization: {result.budget_utilization_pct:.1f}%")

    print("\nOptimal Procurement & Shipping Decisions:")
    if result.decisions:
        print(f"{'Supplier':<25} {'Product':<25} {'Mode':<6} {'Qty':<8} {'Unit $':<8} {'Total Cost':<12}")
        print("-" * 86)
        for d in result.decisions:
            print(f"{d.supplier_name[:24]:<25} {d.product_name[:24]:<25} {d.transport_mode:<6} {d.quantity:<8.0f} ${d.unit_cost:<7.2f} ${d.total_cost:<11.2f}")
    else:
        print("  No procurement allocated (or scenario infeasible).")

    print("\nProjected Ending Inventory:")
    for inv in result.inventory_summary:
        print(f"  - {inv.product_name}: Start={inv.starting_inventory:.0f}, Procured={inv.procured_quantity:.0f}, Demand={inv.demand:.0f} -> Ending={inv.ending_inventory:.0f} (Shortage={inv.shortage_quantity:.0f})")

    if result.constraint_checks:
        print("\nConstraint Audits:")
        for chk in result.constraint_checks:
            print(f"  [{chk.status}] {chk.description} (Slack: {chk.slack:,.2f})")

    if result.warnings:
        print("\nWarnings:")
        for w in result.warnings:
            print(f"  ! {w}")

    if result.infeasibility_diagnostics:
        print("\nInfeasibility Diagnostics:")
        for cause in result.infeasibility_diagnostics.root_causes:
            print(f"  * Root Cause: {cause}")
        for act in result.infeasibility_diagnostics.suggested_actions:
            print(f"  * Suggested Action: {act}")

    print("=" * 80)


if __name__ == "__main__":
    main()
