# SupplyPrescript — Prescriptive Optimization Engine (Phase 4 / Day 11)

## Mathematical Formulation and Business Constraints Specification

### 1. Executive Summary & Business Objective

The **SupplyPrescript Prescriptive Optimization Engine** transitions the system from predictive intelligence (forecasting shipment delays and durations) to prescriptive decision-making.

**Primary Business Objective:**
Minimize total supply-chain cost while maintaining sufficient inventory buffers, adhering strictly to supplier capacities and cash budgets, and satisfying operational delivery-time deadlines.

$$\min Z = C_{\text{procurement}} + C_{\text{shipping}} + C_{\text{holding}} + C_{\text{delay}} + C_{\text{shortage}}$$

The optimizer is implemented in Python using **PuLP (MILP)** and uses the state-of-the-art open-source **HiGHS** simplex/interior-point/branch-and-bound solver (with automated fallbacks to CBC and GLPK).

---

## 2. Indices, Sets, and Parameters

### A. Sets and Indices
- $s \in S$: Active suppliers registered in PostgreSQL (`SUP001` through `SUP050`).
- $p \in P$: Finished products and components (`PROD001` through `PROD100`).
- $m \in M$: Transportation modes ($\text{Road}, \text{Air}, \text{Rail}, \text{Sea}$).
- $(s, p, m) \in \Omega$: Set of eligible candidate procurement and transit routes.

### B. Input Parameters & Units

| Symbol | Parameter | Unit | Source in Repository | Assumption / Fallback |
|---|---|---|---|---|
| $c_{s, p}$ | Supplier unit purchase price | USD ($/unit) | `Product.unit_cost` | Derived from catalog |
| $t_{s, p, m}$ | Transportation cost per unit | USD ($/unit) | `Shipment.shipping_cost / quantity` | Calculated from route distance ($0.04 - $0.35/km) |
| $h_p$ | Inventory holding cost rate | USD ($/unit/period) | Config (`holding_cost_rate = 0.05`) | 5% of unit purchase price per planning period |
| $\pi_p$ | Unmet demand shortage penalty | USD ($/unit) | Config (`shortage_penalty_rate = 1.5`) | 1.5× unit price opportunity penalty |
| $P_{s, p, m}$ | Delay probability | Probability $[0, 1]$ | Active ML Model (`v1.0` XGBoost Classifier) | Dual-model inference output |
| $\delta_{s, p, m}$ | Predicted delay duration | Days | Active ML Model (`v1.0` XGBoost Regressor) | Non-negative clipped regression output |
| $L_j$ | Delay financial impact rate | USD ($/day) | Config (`daily_delay_penalty = 25.0`) | Expected loss: $P \times (\text{penalty} \times \delta / 100)$ |
| $d_{s, p, m}$ | Expected delay cost per unit | USD ($/unit) | Computed: $P_{s, p, m} \times \text{loss\_per\_unit}$ | Interpretable expected-cost estimate |
| $L_{s, m}$ | Baseline transit lead time | Days | `Supplier.base_lead_time` $\times$ mode multiplier | Mode scale: Air (0.4), Road (1.0), Rail (1.4), Sea (2.2) |
| $K_s$ | Supplier capacity limit | Units | `Supplier.capacity` | Default: 5,000 units if null in DB |
| $B$ | Maximum cash budget ceiling | USD ($) | Baseline Scenario: $50,000 | Configurable per scenario |
| $I_{\min}$ | Minimum required ending inventory | Units | Baseline Scenario: 1,000 units | Aggregate ending buffer across all products |
| $D_{\max}$ | Maximum acceptable delay | Days | Baseline Scenario: 7 days | Routes exceeding 7.0 days are prohibited |
| $I_p^0$ | Starting on-hand inventory | Units | `Inventory.inventory_level` | Latest database record per product |
| $R_p$ | Required product demand | Units | `Inventory.demand` / `Product.base_demand` | Authoritative database demand |

---

## 3. Decision Variables

The optimization model strictly distinguishes exogenous input parameters from actual decisions.

### A. Procurement and Shipping Quantity ($q_{s, p, m}$)
- **Definition:** The discrete quantity of product $p$ procured from supplier $s$ shipped using transport mode $m$.
- **Type:** Non-negative Integer (or Continuous if LP relaxation enabled).
- **Bounds:** $0 \le q_{s, p, m} \le K_s$.
- **Derived Quantities:**
  - Total procurement for product $p$: $x_p = \sum_{s \in S, m \in M} q_{s, p, m}$
  - Total procurement from supplier $s$: $x_s = \sum_{p \in P, m \in M} q_{s, p, m}$

### B. Ending Inventory Quantity ($I_p$)
- **Definition:** The physical stock of product $p$ remaining on-hand at the conclusion of the planning horizon.
- **Type:** Non-negative Integer/Continuous ($I_p \ge 0$).

### C. Shortage Quantity ($u_p$)
- **Definition:** Unmet customer demand for product $p$ (slack variable).
- **Type:** Non-negative Integer/Continuous ($0 \le u_p \le R_p$).
- **Strict Fulfillment:** If `allow_shortage: false`, $u_p$ is fixed to 0 ($u_p = 0$).

> **Important Modeling Guardrail:**
> Predicted delay days $\delta_{s, p, m}$ is **never** treated as an independent decision variable. Delay is a conditional outcome predicted by the trained ML pipeline for candidate choices. The optimizer decides **actions** (which supplier, which mode, how many units) that govern exposure to delay.

---

## 4. Objective Function

$$\min Z = \sum_{(s, p, m) \in \Omega} c_{s, p} \cdot q_{s, p, m} + \sum_{(s, p, m) \in \Omega} t_{s, p, m} \cdot q_{s, p, m} + \sum_{p \in P} h_p \cdot I_p + \sum_{(s, p, m) \in \Omega} d_{s, p, m} \cdot q_{s, p, m} + \sum_{p \in P} \pi_p \cdot u_p$$

### Term Descriptions & Economic Interpretations:
1. **Procurement Cost:** $\sum c_{s, p} q_{s, p, m}$ — Direct invoice acquisition expense paid to suppliers.
2. **Transportation Cost:** $\sum t_{s, p, m} q_{s, p, m}$ — Direct freight expense across selected transit modes.
3. **Inventory Holding Cost:** $\sum h_p I_p$ — Capital cost of carrying buffer stock across the planning period.
4. **Expected Delay Cost:** $\sum d_{s, p, m} q_{s, p, m}$ — Probabilistic risk penalty derived from the active XGBoost models:
   $$d_{s, p, m} = P_{s, p, m}(\text{delay}) \times \left( \frac{\text{daily\_delay\_penalty} \times \delta_{s, p, m}}{100} \right)$$
   This avoids arbitrary linear multipliers and links directly to financial risk.
5. **Shortage Penalty:** $\sum \pi_p u_p$ — Economic penalty for unmet demand.

---

## 5. Mathematical Constraints

### Constraint 1 — Cash Budget Ceiling
Total operational cash expenditures (procurement, freight, holding, and delay penalty) must not exceed the configured budget:

$$\sum_{(s, p, m) \in \Omega} (c_{s, p} + t_{s, p, m} + d_{s, p, m}) q_{s, p, m} + \sum_{p \in P} h_p I_p \le B$$

*Note:* Shortage penalties $\pi_p u_p$ represent opportunity loss rather than cash outlays and are excluded from the budget constraint.

### Constraint 2 — Inventory Balance & Flow Conservation
For every product $p \in P$, stock conservation relates starting inventory, incoming procurement, demand, and ending inventory:

$$I_p = I_p^0 + \sum_{s \in S, m \in M} q_{s, p, m} - (R_p - u_p)$$

Standard linear form:
$$\sum_{s \in S, m \in M} q_{s, p, m} - I_p + u_p = R_p - I_p^0, \quad \forall p \in P$$

### Constraint 3 — Minimum Inventory Buffer
The total aggregate ending inventory maintained across all products must satisfy the safety buffer target:

$$\sum_{p \in P} I_p \ge I_{\min} \quad (I_{\min} = 1{,}000 \text{ units})$$

Optional product-specific minimums ($I_p \ge I_{\min, p}$) are also supported.

### Constraint 4 — Maximum Acceptable Delay & Delivery Deadlines
Any transport option whose predicted delay exceeds the maximum acceptable delay threshold is prohibited:

$$q_{s, p, m} = 0, \quad \forall (s, p, m) \text{ where } \delta_{s, p, m} > D_{\max} \quad (D_{\max} = 7.0 \text{ days})$$

If total delivery time deadline $T_{\max}$ is configured:
$$q_{s, p, m} = 0, \quad \forall (s, p, m) \text{ where } L_{s, m} + \delta_{s, p, m} > T_{\max}$$

### Constraint 5 — Supplier Capacity Limits
The total quantity procured from any single supplier $s$ across all products and transit modes cannot exceed that supplier's available capacity:

$$\sum_{p \in P, m \in M} q_{s, p, m} \le K_s, \quad \forall s \in S$$

### Constraint 6 — Non-Negativity & Integrality
$$q_{s, p, m} \ge 0, \quad I_p \ge 0, \quad u_p \ge 0, \quad q_{s, p, m} \in \mathbb{Z}^+, \quad I_p \in \mathbb{Z}^+, \quad u_p \in \mathbb{Z}^+$$

---

## 6. Baseline Scenario Configuration

Located at `config/optimization.yaml`:

```yaml
scenario_name: baseline_supply_chain

budget:
  max_total_cost: 50000
  currency: USD

inventory:
  minimum_required_units: 1000
  holding_cost_rate: 0.05
  shortage_penalty_rate: 1.5

delivery:
  maximum_acceptable_delay_days: 7
  daily_delay_penalty: 25.0

supplier:
  default_max_capacity_units: 5000

optimization:
  objective: minimize_total_cost
  solver: pulp
  time_limit_seconds: 60
  random_seed: 42
```

---

## 7. Execution Guide

Run the optimizer directly from the command line:

```bash
# Execute baseline optimization problem against PostgreSQL database
PYTHONPATH=backend:. backend/.venv/bin/python3 -m optimization.problem
```

### Sample Output:
```text
================================================================================
 SupplyPrescript — Prescriptive Supply Chain Optimization Engine
================================================================================
Scenario: baseline_supply_chain
Budget Limit: 50,000.00 USD
Minimum Inventory Target: 1,000.0 units
Maximum Acceptable Delay: 7.0 days
Solver Engine: pulp (Timeout: 60s)
[INFO] Loaded real database records: 5 products, 150 candidate options.

Executing Prescriptive Optimization Solver...
--------------------------------------------------------------------------------
Status: OPTIMAL (Solver: HiGHS, Time: 0.0126s)
Total Modeled Cost: 33,720.00 USD
Cost Breakdown:
  - Procurement Cost: 27,000.00 USD
  - Shipping Cost: 3,000.00 USD
  - Holding Cost: 3,532.50 USD
  - Expected Delay Cost: 187.50 USD
  - Shortage Penalty Cost: 0.00 USD
Budget Utilization: 67.4%

Optimal Procurement & Shipping Decisions:
Supplier                  Product                   Mode   Qty      Unit $   Total Cost  
--------------------------------------------------------------------------------------
Motherson Sumi Component  STM32 Microcontroller IC  Rail   600      $45.00   $30187.50   

Projected Ending Inventory:
  - STM32 Microcontroller IC: Start=230, Procured=600, Demand=170 -> Ending=660 (Shortage=0)
  - High-Voltage Power Supply 24V: Start=260, Procured=0, Demand=190 -> Ending=70 (Shortage=0)
  - Multi-Layer PCB Board Assembly: Start=290, Procured=0, Demand=210 -> Ending=80 (Shortage=0)
  - Industrial Optical Sensor 50m: Start=320, Procured=0, Demand=230 -> Ending=90 (Shortage=0)
  - TFT LCD Display Module 7-inch: Start=350, Procured=0, Demand=250 -> Ending=100 (Shortage=0)

Constraint Audits:
  [SATISFIED] Budget utilization: 33,720.00 / 50,000.00 USD (Slack: 16,280.00)
  [BINDING] Aggregate ending inventory: 1,000.0 / 1,000.0 units (Slack: 0.00)
================================================================================
```

---

## 8. Feasibility & Diagnostic Architecture

When inputs conflict mathematically, `optimization.validation` detects the cause prior to or after solver execution without relaxing constraints:

1. **Capacity Infeasibility:** When $\sum R_p + I_{\min} - \sum I_p^0 > \sum K_s$ and shortages are disallowed.
2. **Budget Infeasibility:** When minimum required procurement spend exceeds budget $B$.
3. **Delivery Infeasibility:** When all routes for a product exceed $D_{\max} = 7.0$ days.

Diagnostics provide the exact conflicting constraints, calculated deficits, and suggested operational actions.

---

## 9. Verification & Unit Tests

The test suite covers decision variables, constraints, objective terms, feasibility diagnostics, and Pydantic validation:

```bash
# Run optimization unit tests
backend/.venv/bin/pytest optimization/tests/

# Run entire repository test suite (Backend, ML, and Optimization)
backend/.venv/bin/pytest tests/ optimization/tests/
```
Result: **202 / 202 passed** (100% green).
