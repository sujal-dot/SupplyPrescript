# SupplyPrescript — Optimization Engine Technical Specification (Day 12)

**Phase:** 4 — Prescriptive Optimization  
**Module:** `optimization/`  
**Authors:** Senior Optimization Engineer & Supply Chain Data Science Team  
**Date:** October 15, 2026  

---

## 1. System Architecture & Module Responsibilities

The SupplyPrescript Prescriptive Optimization Engine bridges predictive intelligence (shipment delay probabilities and delay durations) with mathematical decision optimization. Built with **PuLP** and powered by the **HiGHS** simplex/interior-point/branch-and-bound solver (with automatic fallbacks to CBC and default MILP solvers), it prescribes cost-optimal procurement and shipping allocations.

```
                              ┌──────────────────────────────┐
                              │  PostgreSQL Schema / Cache   │
                              │  (Suppliers, Products, Inv)  │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
┌─────────────────────────┐       ┌──────────────────────┐
│  ML Prediction Service  │──────▶│ optimization/solver  │◀───── ScenarioConfig
│ (v1.0 XGBoost Clf/Reg)  │       │ (PuLP MILP Problem)  │       (Baseline, Austerity,
└─────────────────────────┘       └──────────┬───────────┘        Delay-Sensitive, Risk)
                                             │
                        ┌────────────────────┼────────────────────┐
                        ▼                    ▼                    ▼
             optimization/variables  optimization/objective  optimization/constraints
              - x[s, p] (Procure)     - Procurement Cost     - Cash Budget ($50k)
              - q[s, p, m] (Ship)     - Freight Cost         - Minimum Inventory (1k)
              - I[p] (Ending Inv)     - Holding Cost         - Supplier Capacity (5k)
              - u[p] (Shortage)       - Delay Penalty        - Delivery Deadline (7d)
                                      - Risk Cost            - Shipment Consistency
                                      - Shortage Penalty     - Inventory Balance
                                             │
                                             ▼
                               ┌───────────────────────────┐
                               │   optimization/results    │
                               │  - OptimizationResult     │
                               │  - Cost Breakdown         │
                               │  - Decision Allocations   │
                               │  - Constraint Audits      │
                               └───────────────────────────┘
```

### Module Responsibilities:

| Module | File | Primary Responsibility |
|---|---|---|
| **Engine Orchestration** | `optimization/solver.py` | PuLP problem assembly, solver resolution, ML enrichment, execution, solution validation, and structured result assembly. |
| **Legacy Entrypoint** | `optimization/problem.py` | CLI execution entrypoint and backwards-compatible bridge to `solver.py`. |
| **Decision Variables** | `optimization/variables.py` | Mathematical variables ($x_{s, p}$, $q_{s, p, m}$, $I_p$, $u_p$), domain definitions, and bounds. |
| **Objective Function** | `optimization/objective.py` | Multi-component cost function ($Z = C_{\text{proc}} + C_{\text{ship}} + C_{\text{inv}} + C_{\text{delay}} + C_{\text{risk}} + C_{\text{short}}$). |
| **Business Constraints** | `optimization/constraints.py` | Budget ceilings, inventory conservation, capacity limits, delivery thresholds, and shipment consistency. |
| **Scenario Management** | `optimization/scenarios.py` | Declarative scenario presets (Baseline, Budget-Constrained, Delay-Sensitive, Risk-Averse) and scenario diff utility. |
| **Configuration** | `optimization/config.py` | Pydantic validated schemas for budgets, delivery, inventory, suppliers, risk, and solvers. |
| **Validation & Diagnostics** | `optimization/validation.py` | Pre-solve domain checks and post-solve root-cause infeasibility diagnostics without silent relaxations. |
| **Result Modeling** | `optimization/results.py` | Pydantic schemas for standardized JSON audit results, decision allocations, and metadata. |

---

## 2. Mathematical Formulation

### A. Indices and Sets
- $s \in S$: Active suppliers (`SUP001` through `SUP050`).
- $p \in P$: Finished products and components (`PROD001` through `PROD100`).
- $m \in M$: Transportation modes ($\text{Road}, \text{Air}, \text{Rail}, \text{Sea}$).
- $(s, p, m) \in \Omega$: Set of eligible candidate supplier-product-transport options.

### B. Decision Variables
- $x_{s, p} \ge 0$: Discrete units purchased from supplier $s$ for product $p$ ($x_{s, p} \in \mathbb{Z}^+$ when `integer_quantities=True`).
- $q_{s, p, m} \ge 0$: Discrete units shipped from supplier $s$ for product $p$ using transport mode $m$ ($q_{s, p, m} \in \mathbb{Z}^+$).
- $I_p \ge 0$: Ending buffer inventory of product $p$ remaining at planning horizon end ($I_p \in \mathbb{Z}^+$).
- $u_p \ge 0$: Unmet customer demand (shortage) for product $p$ ($u_p \in \mathbb{Z}^+$, bounded by demand; $u_p = 0$ if strict fulfillment).

### C. Objective Function
Minimize total expected supply-chain cost:

$$\min Z = C_{\text{procurement}} + C_{\text{shipping}} + C_{\text{inventory}} + C_{\text{delay}} + C_{\text{risk}} + C_{\text{shortage}}$$

Where:
1. **Procurement Cost:**
   $$C_{\text{procurement}} = \sum_{s \in S, p \in P} c_{s, p} \cdot x_{s, p}$$
   Where $c_{s, p}$ is the catalog unit acquisition price in USD.

2. **Shipping Cost:**
   $$C_{\text{shipping}} = \sum_{(s, p, m) \in \Omega} t_{s, p, m} \cdot q_{s, p, m}$$
   Where $t_{s, p, m}$ is the freight cost per unit in USD (derived from route distance and mode rates: Air $0.35/km/unit, Road $0.08, Rail $0.04, Sea $0.02).

3. **Inventory Carrying Cost:**
   $$C_{\text{inventory}} = \sum_{p \in P} h_p \cdot I_p$$
   Where $h_p$ is the periodic carrying cost ($h_p = c_{s, p} \times \text{holding\_cost\_rate}$, default 5% per planning period).

4. **Expected Delay Penalty:**
   $$C_{\text{delay}} = \sum_{(s, p, m) \in \Omega} d_{s, p, m} \cdot q_{s, p, m}$$
   Where $d_{s, p, m} = P_{s, p, m}(\text{delay}) \times \left( \frac{\text{daily\_delay\_penalty} \times \delta_{s, p, m}}{100} \right)$.
   - $P_{s, p, m}(\text{delay})$ is the predicted delay probability $[0, 1]$ from the active v1.0 XGBoost Classifier.
   - $\delta_{s, p, m}$ is the predicted delay duration in days from the active v1.0 XGBoost Regressor.
   - $\text{daily\_delay\_penalty}$ is the configured business contractual penalty ($25.00/day default).

5. **Operational Risk Cost:**
   $$C_{\text{risk}} = \sum_{(s, p, m) \in \Omega} r_s \cdot q_{s, p, m}$$
   Where $r_s = (1.0 - \text{reliability}_s) \times \text{operational\_risk\_cost\_rate}$.
   - Evaluates disruption exposure from historical supplier unreliability without conflating delay days.
   - Set to $0.00 in the Baseline scenario to avoid arbitrary penalty inflation, and actively configured in the Risk-Averse scenario (e.g. $25.00/unit).

6. **Shortage Penalty:**
   $$C_{\text{shortage}} = \sum_{p \in P} \pi_p \cdot u_p$$
   Where $\pi_p = 1.5 \times c_{s, p}$ represents lost opportunity and customer dissatisfaction penalty.

---

## 3. Business Constraints

### Constraint 1 — Cash Budget Ceiling
Total operational cash expenditures must not exceed the configured maximum budget $B$ ($50,000 USD baseline):
$$\sum_{s, p} c_{s, p} x_{s, p} + \sum_{s, p, m} t_{s, p, m} q_{s, p, m} + \sum_p h_p I_p + \mathbf{1}_{\text{delay}} C_{\text{delay}} + \mathbf{1}_{\text{risk}} C_{\text{risk}} \le B$$
*Note:* Non-cash shortage penalties $\pi_p u_p$ represent opportunity loss rather than cash outlays and are excluded from the budget constraint.

### Constraint 2 — Minimum Inventory Safety Buffer
Aggregate ending inventory across all products must satisfy the safety buffer target:
$$\sum_{p \in P} I_p \ge I_{\min} \quad (I_{\min} = 1{,}000 \text{ units})$$
Product-specific minimums ($I_p \ge I_{\min, p}$) are also enforced if specified.

### Constraint 3 — Supplier Capacity Limits
Total procurement from supplier $s$ cannot exceed that supplier's available physical capacity $K_s$ (default fallback: 5,000 units):
$$\sum_{p \in P} x_{s, p} \le K_s, \quad \forall s \in S$$

### Constraint 4 — Demand Fulfillment & Inventory Balance
Flow conservation guarantees that starting inventory, incoming procurement/shipments, and ending inventory balance customer demand:
$$I_p^0 + \sum_{s \in S, m \in M} q_{s, p, m} - (R_p - u_p) = I_p \iff \sum_{s, m} q_{s, p, m} - I_p + u_p = R_p - I_p^0, \quad \forall p \in P$$
If `allow_shortage=False`, strict demand fulfillment forces $u_p = 0$.

### Constraint 5 — Delivery-Time Limit & Pruning
Any candidate transport option whose predicted delay exceeds the maximum acceptable delay threshold ($D_{\max} = 7.0$ days baseline) is prohibited:
$$q_{s, p, m} = 0, \quad \forall (s, p, m) \text{ where } \delta_{s, p, m} > D_{\max}$$
*Limitation Disclosure:* This constraint is prediction-based and depends on statistical ML estimates rather than deterministic delivery guarantees.

### Constraint 6 — Shipment & Procurement Consistency
Shipments allocated across transportation modes cannot exceed procured units from that supplier:
$$\sum_{m \in M} q_{s, p, m} = x_{s, p}, \quad \forall (s, p)$$
Ensures that no units are transported without being purchased, and units are only procured via validated routes.

### Constraint 7 — Non-Negativity & Integrality
$$x_{s, p} \ge 0, \quad q_{s, p, m} \ge 0, \quad I_p \ge 0, \quad u_p \ge 0$$
When whole units are required (`integer_quantities=True`), variables belong to $\mathbb{Z}^+$.

---

## 4. Configurable Scenarios

Scenarios allow evaluating operational trade-offs without altering solver code:

| Scenario | Identifier | Key Parameters | Strategic Purpose |
|---|---|---|---|
| **Scenario A — Baseline** | `baseline` | Budget: $50,000<br>Min Inventory: 1,000<br>Max Delay: 7.0d<br>Delay Penalty: $25/d<br>Risk Cost: $0/unit | Standard operational plan balancing purchasing, freight, holding, and delay costs. |
| **Scenario B — Budget-Constrained** | `budget_constrained` | Budget: $30,000 (configurable)<br>Min Inventory: 1,000<br>Strict Fulfillment: True | Austerity stress-test. Tests whether demand and inventory targets can be met under restricted liquidity. |
| **Scenario C — Delay-Sensitive** | `delay_sensitive` | Max Delay: 3.0d<br>Delay Penalty: $100/d<br>Budget: $75,000 | High service level. Heavily penalizes delays and prohibits routes exceeding 3 days, favoring Air and fast Road transit. |
| **Scenario D — Risk-Averse** | `risk_averse` | Risk Cost Rate: $25/unit<br>Budget: $80,000 | Upstream resilience. Penalizes unreliable suppliers based on historical reliability score, allocating to dependable partners. |

### Scenario Comparison API
```python
from optimization.scenarios import compare_scenarios
from optimization.solver import solve_supply_chain

base_plan = solve_supply_chain(scenario="baseline")
risk_plan = solve_supply_chain(scenario="risk_averse")

diff = compare_scenarios(base_plan, risk_plan)
print(f"Cost Difference: ${diff['objective_difference']:,.2f}")
print("Supplier Allocation Shifts:", diff["supplier_allocation_shifts"])
```

---

## 5. Machine Learning Integration & Limitations

### Integration Architecture
1. **Dual-Model Inference:**
   - Classification: Predicts delay probability $P(\text{delay}) \in [0, 1]$ using `v1.0` XGBoost Classifier.
   - Regression: Predicts delay duration $\delta \ge 0$ days using `v1.0` XGBoost Regressor with non-negative clipping.
2. **In-Memory Caching:**
   - Candidate routes are cached by `(supplier_id, reliability, lead_time, transport_mode, distance)` to prevent duplicate inference passes during problem construction.
3. **Audit Metadata:**
   - The active model version (`v1.0`) and inference timestamp are recorded in the `OptimizationResult.model_metadata` block.

### Critical Counterfactual Limitations
> [!WARNING]
> The ML prediction models were trained on historical observed shipments under specific historical operating conditions. A model trained on observational data cannot guarantee causal invariance when the optimizer recommends switching transport modes or suppliers. Such recommendations reflect predicted estimates under current learned correlations, not guaranteed physical upper bounds.

---

## 6. Execution & Verification

### Running Optimization via CLI
```bash
# Execute optimization engine against PostgreSQL database or benchmark fixture
PYTHONPATH=backend:. backend/.venv/bin/python3 -m optimization.problem
```

### Programmatic Python Usage
```python
from optimization.solver import solve_supply_chain

# High-level execution with custom scenario
result = solve_supply_chain(
    scenario="baseline",
    use_ml_predictions=True,
)

if result.is_optimal():
    print(f"Optimal Cost: ${result.objective_value:,.2f} {result.currency}")
    for d in result.decisions:
        print(f"  {d.supplier_name} -> {d.product_name} via {d.transport_mode}: {d.quantity:.0f} units (${d.total_cost:,.2f})")
else:
    print(f"Solver Status: {result.status}")
    print("Diagnostics:", result.infeasibility_diagnostics.root_causes)
```

### Running Automated Test Suite
```bash
# Run all optimization tests (41 tests)
backend/.venv/bin/pytest optimization/tests/

# Run specific optimization test modules
backend/.venv/bin/pytest optimization/tests/test_solver.py
backend/.venv/bin/pytest optimization/tests/test_scenarios.py
backend/.venv/bin/pytest optimization/tests/test_constraints.py
backend/.venv/bin/pytest optimization/tests/test_objective.py

# Run full repository suite (246 tests)
backend/.venv/bin/pytest
```

---

## 7. Result Schema Specification

Structured optimization outputs return the canonical Day 12 schema:

```json
{
  "status": "OPTIMAL",
  "scenario_id": "baseline",
  "objective_value": 33720.0,
  "currency": "USD",
  "cost_breakdown": {
    "procurement_cost": 27000.0,
    "shipping_cost": 3000.0,
    "inventory_cost": 3532.5,
    "delay_penalty": 187.5,
    "risk_cost": 0.0,
    "shortage_cost": 0.0
  },
  "decisions": [
    {
      "supplier_id": "SUP001",
      "supplier_name": "Apex Micro Electronics",
      "product_id": "PROD001",
      "product_name": "STM32 Microcontroller IC",
      "transport_mode": "Road",
      "quantity": 600.0,
      "unit_cost": 45.0,
      "shipping_cost_per_unit": 5.0,
      "predicted_delay": 0.8,
      "estimated_cost": 30187.5
    }
  ],
  "constraint_checks": [
    {
      "name": "Constraint_Budget_Limit",
      "category": "Budget",
      "status": "SATISFIED",
      "lhs_value": 33720.0,
      "rhs_value": 50000.0,
      "slack": 16280.0,
      "description": "Budget utilization: 33,720.00 / 50,000.00 USD"
    }
  ],
  "warnings": [],
  "model_metadata": {
    "solver": "HiGHS",
    "model_version": "v1.0",
    "prediction_timestamp": "2026-10-15T05:16:32.279059+00:00",
    "solve_time_seconds": 0.0126,
    "variable_count": 154,
    "constraint_count": 161
  }
}
```

---

## 8. Infeasibility Diagnostics & Conflict Analysis

When problem parameters conflict mathematically, the engine prevents solver crashes and avoids silent constraint relaxation. `optimization/validation.py` diagnoses the root causes:

1. **Capacity Deficit:** When $\sum R_p + I_{\min} - \sum I_p^0 > \sum K_s$ and shortages are disallowed.
   - Diagnostic reports exact unit deficit and recommends capacity expansion or inventory buffer reduction.
2. **Budget Infeasibility:** When theoretical cheapest procurement exceeds the cash budget $B$.
   - Diagnostic reports exact dollar gap and suggests necessary budget expansion.
3. **Delivery Deadline Conflict:** When all candidate transportation routes exceed $D_{\max} = 7.0$ days.
   - Diagnostic identifies conflicting routes and suggests realistic threshold adjustments.

---

## 9. Known Assumptions & Limitations

1. **Single-Period Horizon:** Decisions model a single aggregate planning period rather than dynamic rolling multi-echelon horizons.
2. **Linear Unit Pricing:** Pricing assumes constant unit acquisition costs without quantity-tiered bulk volume discounts.
3. **Deterministic Demands:** Demands $R_p$ are treated as known deterministic parameters derived from current PostgreSQL inventory logs; stochastic demand distributions are not modeled in LP form.
4. **Solver Availability:** The engine relies on HiGHS or CBC for MILP branch-and-bound. Continuous LP relaxation is available if integer solvers are absent.
