"""
SupplyPrescript — Prescriptive Optimization Engine
==================================================
Linear and Mixed-Integer Linear Programming (MILP) optimization module.
Prescribes cost-optimal supply-chain allocations minimizing total procurement,
shipping, holding, and delay penalty costs subject to budget, capacity, inventory,
and delivery constraints.
"""

from optimization.config import (
    BudgetConfig,
    DeliveryConfig,
    InventoryConfig,
    RiskConfig,
    ScenarioConfig,
    SolverConfig,
    SupplierConfig,
    load_scenario_config,
)
from optimization.constraints import (
    AppliedConstraint,
    ConstraintRegistry,
    apply_business_constraints,
)
from optimization.objective import (
    ObjectiveExpressions,
    build_objective,
)
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
from optimization.scenarios import (
    compare_scenarios,
    create_scenario,
    get_baseline_scenario,
    get_budget_constrained_scenario,
    get_delay_sensitive_scenario,
    get_expedited_service_scenario,
    get_inventory_buffering_scenario,
    get_risk_averse_scenario,
    list_available_scenarios,
)
from optimization.solver import (
    build_optimization_problem,
    enrich_candidate_options_with_ml,
    solve_optimization_problem,
    solve_supply_chain,
)
from optimization.validation import (
    InfeasibilityDiagnostic,
    PreSolveValidationReport,
    ValidationError,
    diagnose_infeasibility,
    validate_optimization_inputs,
)
from optimization.variables import (
    CandidateOption,
    OptimizationVariables,
    ProductData,
    create_decision_variables,
)
from optimization.decision_schemas import (
    AlternativeOption,
    BaselineSummary,
    ConstraintViolation,
    FeasibilityStatus,
    RecommendationStatus,
    RiskLevel,
    SolutionValidationReport,
    AlternativeEvaluationResponse,
    AlternativeGenerationRequest,
    OptimizationRequest,
    OptimizationResponse,
    OptimizationOption,
    OptimizationPredictionSummary,
    OptimizationConstraintCheck,
    OptimizationMetadata,
)
from optimization.alternatives import (
    generate_alternatives_for_shipment,
    generate_option_a_air_freight,
    generate_option_b_secondary_supplier,
    generate_option_c_delay_launch,
    build_baseline_summary,
)
from optimization.alternative_evaluator import (
    evaluate_alternatives,
    validate_optimization_solution,
    is_recommendation_eligible,
    calculate_objective_cost,
)
from optimization.decision_ranker import (
    rank_alternatives,
)

__all__ = [
    # Config
    "BudgetConfig",
    "DeliveryConfig",
    "InventoryConfig",
    "RiskConfig",
    "ScenarioConfig",
    "SolverConfig",
    "SupplierConfig",
    "load_scenario_config",
    # Variables
    "CandidateOption",
    "ProductData",
    "OptimizationVariables",
    "create_decision_variables",
    # Objective
    "ObjectiveExpressions",
    "build_objective",
    # Constraints
    "AppliedConstraint",
    "ConstraintRegistry",
    "apply_business_constraints",
    # Validation
    "ValidationError",
    "PreSolveValidationReport",
    "InfeasibilityDiagnostic",
    "validate_optimization_inputs",
    "diagnose_infeasibility",
    "validate_optimization_solution",
    "is_recommendation_eligible",
    "SolutionValidationReport",
    # Problem & Solver
    "build_optimization_problem",
    "solve_supply_chain",
    "solve_optimization_problem",
    "enrich_candidate_options_with_ml",
    "load_optimization_data_from_db",
    # Results
    "OptimizationResult",
    "ObjectiveSummary",
    "ConstraintSummary",
    "DecisionAllocation",
    "InventoryResult",
    "ConstraintCheckResult",
    "SupplierCapacityUtilization",
    "InfeasibilityReport",
    # Scenarios
    "get_baseline_scenario",
    "get_budget_constrained_scenario",
    "get_delay_sensitive_scenario",
    "get_risk_averse_scenario",
    "get_expedited_service_scenario",
    "get_inventory_buffering_scenario",
    "list_available_scenarios",
    "create_scenario",
    "compare_scenarios",
    # Day 13 Prescriptive Decisions
    "AlternativeOption",
    "BaselineSummary",
    "ConstraintViolation",
    "FeasibilityStatus",
    "RecommendationStatus",
    "RiskLevel",
    "AlternativeEvaluationResponse",
    "AlternativeGenerationRequest",
    "generate_alternatives_for_shipment",
    "generate_option_a_air_freight",
    "generate_option_b_secondary_supplier",
    "generate_option_c_delay_launch",
    "build_baseline_summary",
    "evaluate_alternatives",
    "calculate_objective_cost",
    "rank_alternatives",
    # Day 14 Optimization API Schemas
    "OptimizationRequest",
    "OptimizationResponse",
    "OptimizationOption",
    "OptimizationPredictionSummary",
    "OptimizationConstraintCheck",
    "OptimizationMetadata",
]


def __getattr__(name: str):
    if name in ("build_optimization_problem", "solve_optimization_problem", "solve_supply_chain", "load_optimization_data_from_db"):
        from optimization.problem import (
            build_optimization_problem,
            load_optimization_data_from_db,
            solve_optimization_problem,
            solve_supply_chain,
        )
        mapping = {
            "build_optimization_problem": build_optimization_problem,
            "solve_supply_chain": solve_supply_chain,
            "solve_optimization_problem": solve_optimization_problem,
            "load_optimization_data_from_db": load_optimization_data_from_db,
        }
        return mapping[name]
    raise AttributeError(f"module 'optimization' has no attribute '{name}'")
