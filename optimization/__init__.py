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
    create_scenario,
    get_baseline_scenario,
    get_budget_constrained_scenario,
    get_expedited_service_scenario,
    get_inventory_buffering_scenario,
    list_available_scenarios,
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

__all__ = [
    # Config
    "BudgetConfig",
    "DeliveryConfig",
    "InventoryConfig",
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
    # Problem & Solver
    "build_optimization_problem",
    "solve_optimization_problem",
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
    "get_expedited_service_scenario",
    "get_inventory_buffering_scenario",
    "list_available_scenarios",
    "create_scenario",
]


def __getattr__(name: str):
    if name in ("build_optimization_problem", "solve_optimization_problem", "load_optimization_data_from_db"):
        from optimization.problem import (
            build_optimization_problem,
            load_optimization_data_from_db,
            solve_optimization_problem,
        )
        mapping = {
            "build_optimization_problem": build_optimization_problem,
            "solve_optimization_problem": solve_optimization_problem,
            "load_optimization_data_from_db": load_optimization_data_from_db,
        }
        return mapping[name]
    raise AttributeError(f"module 'optimization' has no attribute '{name}'")
