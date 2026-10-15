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
    risk_cost: pulp.LpAffineExpression
    shortage_cost: pulp.LpAffineExpression
    total_cost: pulp.LpAffineExpression

    # Cash expenditure portion (excluding non-cash opportunity shortage penalties)
    cash_expenditure: pulp.LpAffineExpression

    @property
    def inventory_cost(self) -> pulp.LpAffineExpression:
        """Alias for holding_cost matching standard supply chain reporting schema."""
        return self.holding_cost

    @property
    def delay_penalty(self) -> pulp.LpAffineExpression:
        """Alias for delay_cost matching standard supply chain reporting schema."""
        return self.delay_cost


def build_objective(
    problem: pulp.LpProblem,
    variables: OptimizationVariables,
    candidate_options: List[CandidateOption],
    products: List[ProductData],
    config: ScenarioConfig,
) -> ObjectiveExpressions:
    """
    Constructs the multi-component objective function:
        min Z = C_procurement + C_shipping + C_inventory + C_delay + C_risk + C_shortage
    and assigns it to the PuLP problem.
    """
    options_by_key = {
        (opt.supplier_id, opt.product_id, opt.transport_mode): opt
        for opt in candidate_options
    }
    products_by_id = {prod.product_id: prod for prod in products}

    # 1. Procurement Cost: sum_{s, p} c_{s, p} * x_{s, p} (or fallback to sum_{s, p, m} c_{s, p} * q)
    procurement_terms = []
    if variables.x:
        pair_costs: Dict[Tuple[str, str], float] = {}
        for opt in candidate_options:
            pair = (opt.supplier_id, opt.product_id)
            if pair not in pair_costs:
                pair_costs[pair] = opt.unit_cost
        for pair, var_x in variables.x.items():
            u_cost = pair_costs.get(pair, 0.0)
            if u_cost > 0:
                procurement_terms.append(u_cost * var_x)
    else:
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

    # 3. Holding / Inventory Cost: sum_p h_p * I_p
    holding_terms = []
    for p_id, var_inv in variables.I.items():
        prod = products_by_id.get(p_id)
        if prod and prod.holding_cost_per_unit > 0:
            holding_terms.append(prod.holding_cost_per_unit * var_inv)
    holding_cost = pulp.lpSum(holding_terms) if holding_terms else 0.0

    # 4. Expected Delay Penalty Cost: sum_{s, p, m} d_{s, p, m} * q_{s, p, m}
    # d_{s, p, m} = P(delay) * (daily_delay_penalty * predicted_delay_days / 100)
    delay_terms = []
    for key, var in variables.q.items():
        opt = options_by_key.get(key)
        if opt and opt.expected_delay_cost_per_unit > 0:
            delay_terms.append(opt.expected_delay_cost_per_unit * var)
    delay_cost = pulp.lpSum(delay_terms) if delay_terms else 0.0

    # 5. Operational Risk Cost: sum_{s, p, m} risk_cost_per_unit * q_{s, p, m}
    # Based on supplier unreliability (1 - reliability) * operational_risk_cost_rate
    risk_terms = []
    risk_rate = config.risk.operational_risk_cost_rate if hasattr(config, "risk") else 0.0
    is_risk_enabled = config.risk.enabled if hasattr(config, "risk") else False

    if is_risk_enabled and risk_rate > 0:
        for key, var in variables.q.items():
            opt = options_by_key.get(key)
            if opt:
                unit_risk = (
                    opt.expected_risk_cost_per_unit
                    if opt.expected_risk_cost_per_unit > 0
                    else max(0.0, (1.0 - getattr(opt, "supplier_reliability", 1.0))) * risk_rate
                )
                if unit_risk > 0:
                    risk_terms.append(unit_risk * var)
    risk_cost = pulp.lpSum(risk_terms) if risk_terms else 0.0

    # 6. Shortage Penalty Cost: sum_p pi_p * u_p
    shortage_terms = []
    for p_id, var_short in variables.u.items():
        prod = products_by_id.get(p_id)
        if prod and prod.shortage_penalty_per_unit > 0:
            shortage_terms.append(prod.shortage_penalty_per_unit * var_short)
    shortage_cost = pulp.lpSum(shortage_terms) if shortage_terms else 0.0

    # Total Cost Objective: minimize Z
    total_cost = procurement_cost + shipping_cost + holding_cost + delay_cost + risk_cost + shortage_cost

    # Cash expenditure portion for budget constraint (excludes non-cash opportunity shortage penalty)
    cash_parts = [procurement_cost, shipping_cost, holding_cost]
    if getattr(config.budget, "include_expected_delay_penalty", True):
        cash_parts.append(delay_cost)
    if getattr(config.budget, "include_risk_cost", False):
        cash_parts.append(risk_cost)
    cash_expenditure = pulp.lpSum(cash_parts)

    # Assign objective to PuLP problem
    problem += total_cost, "Minimize_Total_Supply_Chain_Cost"

    logger.debug("Configured objective with 6 cost components: procurement, shipping, holding, delay, risk, shortage.")
    return ObjectiveExpressions(
        procurement_cost=procurement_cost,
        shipping_cost=shipping_cost,
        holding_cost=holding_cost,
        delay_cost=delay_cost,
        risk_cost=risk_cost,
        shortage_cost=shortage_cost,
        total_cost=total_cost,
        cash_expenditure=cash_expenditure,
    )
