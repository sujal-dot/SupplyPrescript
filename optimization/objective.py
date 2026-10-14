"""
SupplyPrescript — Optimization Objective Function
=================================================
Defines the total supply chain cost objective function:

    min Z = C_procurement + C_shipping + C_holding + C_delay + C_shortage

Where:
- C_procurement = sum_{s, p, m} (c_{s, p} * q_{s, p, m})
- C_shipping    = sum_{s, p, m} (t_{s, p, m} * q_{s, p, m})
- C_holding     = sum_p (h_p * I_p)
- C_delay       = sum_{s, p, m} (d_{s, p, m} * q_{s, p, m})
- C_shortage    = sum_p (pi_p * u_p)

Units: All cost components are strictly denominated in the configured currency (USD).
Delay cost uses an interpretable expected-loss formulation:
    d_{s, p, m} = P(delay)_{s, p, m} * (daily_delay_penalty * predicted_delay_days_{s, p, m} / lot_scale)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List

import pulp

from optimization.config import ScenarioConfig
from optimization.variables import CandidateOption, OptimizationVariables, ProductData

logger = logging.getLogger("optimization.objective")


@dataclass
class ObjectiveExpressions:
    """
    Holds individual affine expressions for each supply chain cost component.
    Enables granular cost breakdown and budget accounting.
    """
    procurement_cost: pulp.LpAffineExpression
    shipping_cost: pulp.LpAffineExpression
    holding_cost: pulp.LpAffineExpression
    delay_cost: pulp.LpAffineExpression
    shortage_cost: pulp.LpAffineExpression
    total_cost: pulp.LpAffineExpression

    # Cash expenditure portion (excluding non-cash opportunity shortage penalties)
    cash_expenditure: pulp.LpAffineExpression


def build_objective(
    problem: pulp.LpProblem,
    variables: OptimizationVariables,
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> ObjectiveExpressions:
    """
    Constructs the multi-component objective function and assigns it to the PuLP problem.
    """
    options_by_key = {
        (opt.supplier_id, opt.product_id, opt.transport_mode): opt
        for opt in candidate_options
    }
    products_by_id = {prod.product_id: prod for prod in products}

    # 1. Procurement Cost: sum_{s, p, m} c_{s, p} * q_{s, p, m}
    procurement_terms = []
    for key, var in variables.q.items():
        opt = options_by_key.get(key)
        if opt and opt.unit_cost > 0:
            procurement_terms.append(opt.unit_cost * var)
    procurement_cost = pulp.lpSum(procurement_terms) if procurement_terms else 0.0

    # 2. Shipping Cost: sum_{s, p, m} t_{s, p, m} * q_{s, p, m}
    shipping_terms = []
    for key, var in variables.q.items():
        opt = options_by_key.get(key)
        if opt and opt.shipping_cost_per_unit > 0:
            shipping_terms.append(opt.shipping_cost_per_unit * var)
    shipping_cost = pulp.lpSum(shipping_terms) if shipping_terms else 0.0

    # 3. Holding Cost: sum_p h_p * I_p
    holding_terms = []
    for p_id, var_inv in variables.I.items():
        prod = products_by_id.get(p_id)
        if prod and prod.holding_cost_per_unit > 0:
            holding_terms.append(prod.holding_cost_per_unit * var_inv)
    holding_cost = pulp.lpSum(holding_terms) if holding_terms else 0.0

    # 4. Expected Delay Cost: sum_{s, p, m} d_{s, p, m} * q_{s, p, m}
    # d_{s, p, m} = P(delay) * expected_loss_per_unit
    delay_terms = []
    for key, var in variables.q.items():
        opt = options_by_key.get(key)
        if opt and opt.expected_delay_cost_per_unit > 0:
            delay_terms.append(opt.expected_delay_cost_per_unit * var)
    delay_cost = pulp.lpSum(delay_terms) if delay_terms else 0.0

    # 5. Shortage Penalty Cost: sum_p pi_p * u_p
    shortage_terms = []
    for p_id, var_short in variables.u.items():
        prod = products_by_id.get(p_id)
        if prod and prod.shortage_penalty_per_unit > 0:
            shortage_terms.append(prod.shortage_penalty_per_unit * var_short)
    shortage_cost = pulp.lpSum(shortage_terms) if shortage_terms else 0.0

    # Total Cost Objective: minimize Z
    total_cost = procurement_cost + shipping_cost + holding_cost + delay_cost + shortage_cost

    # Cash expenditure portion for budget constraint (excludes non-cash shortage penalty)
    cash_expenditure = procurement_cost + shipping_cost + holding_cost + delay_cost

    # Assign objective to PuLP problem
    problem += total_cost, "Minimize_Total_Supply_Chain_Cost"

    logger.debug("Configured objective with 5 cost components: procurement, shipping, holding, delay, shortage.")
    return ObjectiveExpressions(
        procurement_cost=procurement_cost,
        shipping_cost=shipping_cost,
        holding_cost=holding_cost,
        delay_cost=delay_cost,
        shortage_cost=shortage_cost,
        total_cost=total_cost,
        cash_expenditure=cash_expenditure,
    )
