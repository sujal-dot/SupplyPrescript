"""
SupplyPrescript — Prescriptive Decision Ranker & Recommendation Engine
======================================================================
Ranks feasible supply-chain alternatives using the Day 12 multi-component objective:
    min Z = C_total + C_delay + C_risk

Applies strict recommendation safety gating:
- Excludes alternatives that violate mandatory business constraints.
- Identifies trade-offs between speed, cost, and reliability.
- Returns NO_FEASIBLE_OPTION when no alternative satisfies constraints.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from optimization.alternative_evaluator import is_recommendation_eligible
from optimization.config import ScenarioConfig
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    FeasibilityStatus,
    RecommendationStatus,
    SolutionValidationReport,
)

logger = logging.getLogger("optimization.decision_ranker")


def rank_alternatives(
    alternatives: List[AlternativeOption],
    baseline: BaselineSummary,
    config: ScenarioConfig,
    validation_reports: Optional[Dict[str, SolutionValidationReport]] = None,
) -> Tuple[List[AlternativeOption], Optional[str], RecommendationStatus, str, str]:
    """
    Rank alternatives and formulate the final prescriptive recommendation.

    Returns:
        (ranked_options, recommended_option_id, status, recommendation_reason, trade_off_analysis)
    """
    reports = validation_reports or {}

    # 1. Apply Recommendation Safety Gate: Filter strictly eligible feasible options
    eligible_options: List[AlternativeOption] = []
    ineligible_reasons: List[str] = []

    for opt in alternatives:
        rep = reports.get(opt.option_id)
        if rep is not None:
            eligible = is_recommendation_eligible(opt, rep)
        else:
            eligible = (opt.feasibility == FeasibilityStatus.FEASIBLE) and (len(opt.constraint_violations) == 0)

        if eligible:
            eligible_options.append(opt)
        else:
            v_msgs = [v.message for v in opt.constraint_violations]
            reason = f"Option {opt.option_id} ({opt.name}): {'; '.join(v_msgs) if v_msgs else opt.explanation}"
            ineligible_reasons.append(reason)

    # 2. Case: Zero eligible alternatives -> NO_FEASIBLE_OPTION
    if not eligible_options:
        trade_offs = (
            "No candidate alternative satisfies all hard business constraints (budget ceiling, "
            "delivery deadline, and supplier capacity). Operational escalation or constraint relaxation is required."
        )
        reason = f"NO_FEASIBLE_OPTION: All evaluated alternatives were rejected by business constraints: {'; '.join(ineligible_reasons)}"

        # Ensure all are marked is_recommended = False
        final_options = [o.model_copy(update={"is_recommended": False}) for o in alternatives]
        return final_options, None, RecommendationStatus.NO_FEASIBLE_OPTION, reason, trade_offs

    # 3. Sort eligible options by Day 12 Objective Z (ascending)
    # Tie-breakers: lower delay probability, then lower predicted delay days
    def sort_key(o: AlternativeOption) -> Tuple[float, float, float]:
        z = o.objective_value if o.objective_value is not None else float("inf")
        prob = o.delay_probability if o.delay_probability is not None else 1.0
        days = o.predicted_delay_days if o.predicted_delay_days is not None else 100.0
        return (z, prob, days)

    eligible_options.sort(key=sort_key)
    winner = eligible_options[0]

    # 4. Formulate trade-off analysis and justification
    trade_off_lines: List[str] = []
    for opt in alternatives:
        status_tag = f"[{opt.feasibility.value}]"
        cost_str = f"${opt.estimated_total_cost:,.2f}" if opt.estimated_total_cost is not None else "Unknown"
        delta_str = f"({opt.additional_cost_percentage:+.1f}%)" if opt.additional_cost_percentage is not None else ""
        del_str = f"{opt.estimated_delivery_days:.1f} days" if opt.estimated_delivery_days is not None else "Unknown"
        z_str = f"Objective Z=${opt.objective_value:,.2f}" if opt.objective_value is not None else "N/A"
        trade_off_lines.append(f"• Option {opt.option_id} ({opt.name}) {status_tag}: Cost={cost_str} {delta_str}, Delivery={del_str}, {z_str}")

    trade_off_analysis = "\n".join(trade_off_lines)

    # Winner specific reasoning
    w_cost = f"${winner.estimated_total_cost:,.2f}" if winner.estimated_total_cost is not None else "$0"
    w_delta = f"${winner.additional_cost:,.2f}" if winner.additional_cost is not None else "$0"
    w_del = f"{winner.estimated_delivery_days:.1f} days" if winner.estimated_delivery_days is not None else "on-time"
    w_z = f"${winner.objective_value:,.2f}" if winner.objective_value is not None else "$0"

    reason = (
        f"Option {winner.option_id} ({winner.name}) is recommended with optimal Day 12 objective cost {w_z}. "
        f"It achieves feasible delivery in {w_del} (incremental cost {w_delta}) while strictly adhering to "
        f"the ${config.budget.max_total_cost:,.2f} budget ceiling and operational capacity limits."
    )

    # Mark winner in returned options
    final_options: List[AlternativeOption] = []
    for opt in alternatives:
        is_win = (opt.option_id == winner.option_id)
        final_options.append(opt.model_copy(update={"is_recommended": is_win}))

    return final_options, winner.option_id, RecommendationStatus.FEASIBLE_RECOMMENDATION, reason, trade_off_analysis
