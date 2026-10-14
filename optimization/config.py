"""
SupplyPrescript — Optimization Engine Configuration
===================================================
Centralized, validated configuration schemas for the prescriptive optimization engine.
Defines budget scopes, inventory targets, delivery constraints, supplier capacities,
and solver parameters for baseline and counterfactual scenarios.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger("optimization.config")

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "optimization.yaml"


class BudgetConfig(BaseModel):
    max_total_cost: float = Field(
        50000.0,
        gt=0,
        description="Maximum procurement, shipping, inventory holding, and delay expenditure permitted during planning horizon ($)",
    )
    currency: str = Field(
        "USD",
        min_length=3,
        max_length=3,
        description="Currency code (e.g. USD, EUR, INR)",
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        code = v.strip().upper()
        if len(code) != 3 or not code.isalpha():
            raise ValueError(f"Invalid currency code '{v}'. Must be a 3-letter ISO code.")
        return code


class InventoryConfig(BaseModel):
    minimum_required_units: float = Field(
        1000.0,
        ge=0,
        description="Minimum inventory quantity that must be maintained across all products or per product",
    )
    holding_cost_rate: float = Field(
        0.05,
        ge=0,
        description="Holding cost rate per unit as fraction of unit cost per planning period (default 5%)",
    )
    shortage_penalty_rate: float = Field(
        1.5,
        ge=0,
        description="Shortage penalty multiplier relative to unit price for unmet demand ($/unit)",
    )


class DeliveryConfig(BaseModel):
    maximum_acceptable_delay_days: float = Field(
        7.0,
        ge=0,
        description="Maximum acceptable predicted delay duration in days before candidate option is deemed infeasible",
    )
    daily_delay_penalty: float = Field(
        25.0,
        ge=0,
        description="Financial impact or contract penalty rate per day of delay ($/day/shipment)",
    )
    max_total_lead_time_days: Optional[float] = Field(
        None,
        gt=0,
        description="Optional hard upper bound on total delivery duration (baseline lead time + predicted delay days)",
    )


class SupplierConfig(BaseModel):
    default_max_capacity_units: float = Field(
        5000.0,
        gt=0,
        description="Default fallback maximum supplier capacity when database record is unavailable (units)",
    )
    use_individual_capacities: bool = Field(
        True,
        description="If True, use individual database supplier capacities; fallback to default only when missing",
    )


class SolverConfig(BaseModel):
    objective: str = Field(
        "minimize_total_cost",
        description="Objective optimization target (e.g. minimize_total_cost)",
    )
    solver: str = Field(
        "pulp",
        description="Solver engine identifier (e.g. pulp, highs, cbc)",
    )
    time_limit_seconds: int = Field(
        60,
        gt=0,
        description="Maximum solver execution time before timeout",
    )
    random_seed: int = Field(
        42,
        description="Deterministic random seed for solver routines",
    )
    allow_shortage: bool = Field(
        True,
        description="If True, unmet demand is allowed as a decision variable penalized in objective; if False, 100% fulfilled",
    )
    integer_quantities: bool = Field(
        True,
        description="If True, enforce integer whole-unit decision variables; if False, solve as continuous LP relaxation",
    )
    msg: bool = Field(
        False,
        description="If True, enable verbose solver log output",
    )


class ScenarioConfig(BaseModel):
    scenario_name: str = Field(
        "baseline_supply_chain",
        min_length=1,
        description="Human-readable scenario identifier",
    )
    description: Optional[str] = Field(
        None,
        description="Detailed scenario assumption description",
    )
    budget: BudgetConfig = Field(default_factory=BudgetConfig)
    inventory: InventoryConfig = Field(default_factory=InventoryConfig)
    delivery: DeliveryConfig = Field(default_factory=DeliveryConfig)
    supplier: SupplierConfig = Field(default_factory=SupplierConfig)
    optimization: SolverConfig = Field(default_factory=SolverConfig)


def load_scenario_config(
    path: Optional[Union[str, Path]] = None,
    overrides: Optional[Dict[str, Any]] = None,
) -> ScenarioConfig:
    """
    Load and validate optimization scenario configuration from YAML file or dictionary.
    Applies any runtime parameter overrides without altering on-disk source files.
    """
    target_path = Path(path) if path else DEFAULT_CONFIG_PATH
    data: Dict[str, Any] = {}

    if target_path.exists():
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f)
                if isinstance(loaded, dict):
                    data = loaded
                else:
                    logger.warning("Config at %s did not parse as a dictionary.", target_path)
        except Exception as exc:
            logger.error("Failed to read configuration YAML at %s: %s", target_path, exc)
            raise ValueError(f"Could not load optimization configuration from {target_path}: {exc}") from exc
    elif path is not None:
        raise FileNotFoundError(f"Specified configuration file does not exist: {path}")
    else:
        logger.info("Configuration file %s not found. Initializing standard baseline defaults.", target_path)

    if overrides:
        # Deep merge simple overrides
        for key, value in overrides.items():
            if isinstance(value, dict) and key in data and isinstance(data[key], dict):
                data[key].update(value)
            else:
                data[key] = value

    return ScenarioConfig(**data)


def get_baseline_scenario() -> ScenarioConfig:
    """
    Returns the authoritative baseline planning scenario as defined in Day 11 specifications:
    - Budget: $50,000 USD max total cost
    - Minimum Inventory: 1,000 units aggregate requirement
    - Delivery: Maximum acceptable delay <= 7 days
    - Supplier: Default max capacity 5,000 units (individual DB capacities take precedence)
    - Optimization: Minimize total cost, PuLP solver, 60s timeout, random seed 42
    """
    return ScenarioConfig(
        scenario_name="baseline_supply_chain",
        description="Standard baseline operational planning scenario with moderate budget and risk tolerance",
        budget=BudgetConfig(max_total_cost=50000.0, currency="USD"),
        inventory=InventoryConfig(minimum_required_units=1000.0, holding_cost_rate=0.05, shortage_penalty_rate=1.5),
        delivery=DeliveryConfig(maximum_acceptable_delay_days=7.0, daily_delay_penalty=25.0),
        supplier=SupplierConfig(default_max_capacity_units=5000.0, use_individual_capacities=True),
        optimization=SolverConfig(
            objective="minimize_total_cost",
            solver="pulp",
            time_limit_seconds=60,
            random_seed=42,
            allow_shortage=True,
            integer_quantities=True,
        ),
    )
