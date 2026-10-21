# Prescriptive Decision Engine — Three Alternative Decisions (Day 13)

**Phase:** 4 — Prescriptive Optimization  
**Module:** `optimization.alternatives`, `optimization.alternative_evaluator`, `optimization.decision_ranker`  
**API Endpoints:** `POST /api/optimization/alternatives`, `GET /api/optimization/alternatives/{shipment_id}`  

---

## 1. Overview and Business Context

When machine learning inference identifies a shipment facing elevated delay risk (e.g. delay probability $\ge 0.30$ or predicted delay days $\ge 3.0$), supply-chain planners require concrete, actionable operational decisions rather than passive notifications.

The **SupplyPrescript Prescriptive Alternative Engine** automatically generates, evaluates, and ranks three distinct operational strategies:

1. **Option A — Expedite with Air Freight:** Speed up transit by shifting the transport modality from Road/Rail to Air.
2. **Option B — Switch to a Secondary Supplier:** Divert order volume to an eligible alternative vendor with verified capacity and high historical reliability.
3. **Option C — Delay Product Launch / Milestone:** Postpone the launch or assembly milestone to absorb the predicted delay without incurring additional logistics freight.

Each option is rigorously audited against the hard business constraints established in Day 11/12, scored via the multi-component Day 12 objective function, and filtered through an independent recommendation safety gate.

---

## 2. Decision Formulation & Mathematical Calculations

### Baseline Quantification
Given a target shipment record $k$:
- Order quantity: $Q_k$
- Unit procurement cost: $C_{u, k}$
- Baseline freight: $C_{\text{ship}, k}$
- Planned lead time: $L_k$ days
- ML predicted delay duration: $\Delta d_k$ days
- ML predicted delay probability: $P(\text{delay}_k)$
- Baseline total expenditure:
  $$C_{\text{baseline}} = (Q_k \times C_{u, k}) + C_{\text{ship}, k}$$
- Total expected delivery duration:
  $$T_{\text{baseline}} = L_k + \Delta d_k$$

---

### Option A — Expedite with Air Freight

* **Operational Concept:** Utilizes high-speed commercial air cargo corridor to compress transit duration.
* **Route & Rate Calculations:**
  - Route distance $d_{\text{hub}}$ is determined dynamically using the hub distance matrix between supplier origin and shipment destination.
  - Freight cost rate for Air is configured at $\$0.35$ per km per 100 units ($\$0.0035$/km/unit) with a $\$50.00$ minimum handling floor:
    $$C_{\text{shipping}, A} = \max\left(50.0, \frac{d_{\text{hub}} \times 0.35 \times Q_k}{100.0}\right)$$
  - Modal lead time: Air modality applies a nominal $0.4\times$ multiplier to base lead time (minimum $1.0$ day):
    $$L_A = \max(1.0, \text{round}(L_{\text{base}} \times 0.4, 1))$$
  - ML Inference: The active registered model (`v1.0 XGBoost`) is evaluated with `transport_mode="Air"`, `lead_time=L_A`, `shipping_cost=C_{shipping, A}`, yielding updated $P(\text{delay}_A)$ and $\Delta d_A$.
  - Additional cost:
    $$\Delta C_A = C_{\text{total}, A} - C_{\text{baseline}}$$
    $$\%\Delta C_A = \frac{\Delta C_A}{C_{\text{baseline}}} \times 100\%$$
  - Total arrival duration: $T_A = L_A + \Delta d_A$.

---

### Option B — Switch to a Secondary Supplier

* **Operational Concept:** Reroutes demand to a qualified secondary supplier registered in PostgreSQL capable of supplying the product SKU.
* **Calculations:**
  - Identifies alternative suppliers $s' \neq s_{\text{baseline}}$ where capacity $K_{s'} \ge Q_k$.
  - Secondary unit cost $C_{u, B}$ is resolved from the supplier catalog (or baseline unit cost).
  - Highway distance $d_{s'}$ from secondary supplier origin to destination is calculated.
  - Road shipping freight:
    $$C_{\text{shipping}, B} = \max\left(30.0, \frac{d_{s'} \times 0.08 \times Q_k}{100.0}\right)$$
  - Model scoring: ML models are queried with secondary supplier features (historical reliability, lead time $L_{s'}$, road distance $d_{s'}$), generating $P(\text{delay}_B)$ and $\Delta d_B$.
  - Cost deltas:
    $$\Delta C_B = C_{\text{total}, B} - C_{\text{baseline}}$$
    $$\%\Delta C_B = \frac{\Delta C_B}{C_{\text{baseline}}} \times 100\%$$
* **Insufficient Data Handling:** If no active secondary supplier has verified capacity for the product, Option B returns `feasibility: INSUFFICIENT_DATA` with an explicit diagnostic note rather than inventing fake vendor data.

---

### Option C — Delay Product Launch / Milestone

* **Operational Concept:** Accepts shipment delay and pushes back downstream milestones.
* **Calculations:**
  - Schedule impact: $\Delta t_C = \Delta d_k$ (predicted delay days).
  - Total arrival duration: $T_C = L_k + \Delta d_k$.
  - Direct logistics freight delta: $\$0.00$.
* **Commercial Impact Handling:**
  - If a daily commercial penalty or revenue loss rate $R_{\text{launch}}$ is configured in business metadata:
    $$\text{Commercial Loss} = \Delta t_C \times R_{\text{launch}}$$
  - If commercial impact is unconfigured: Option C explicitly returns `feasibility: INSUFFICIENT_DATA`, `schedule_impact_days: delta_t`, and documents that commercial revenue loss is unquantified in business metadata.

---

## 3. Prescriptive Ranking & Recommendation Safety Gate

### Day 12 Objective Scoring
Each alternative is evaluated using the composite Day 12 objective function:
$$\min Z = C_{\text{total}} + C_{\text{delay}} + C_{\text{risk}}$$
Where:
- $C_{\text{total}} = C_{\text{procurement}} + C_{\text{shipping}} + C_{\text{shortage}}$
- $C_{\text{delay}} = \text{daily\_delay\_penalty} \times \text{predicted\_delay\_days} \times P(\text{delay})$
- $C_{\text{risk}} = \text{operational\_risk\_cost\_rate} \times (1 - \text{reliability}) \times Q_k$

### Independent Validation & Safety Gating
An alternative is eligible for recommendation **if and only if** `is_recommendation_eligible(alt, report)` returns `True`:
1. `feasibility == FEASIBLE`
2. Total budgeted cost $C_{\text{budgeted}} \le B_{\max} + \epsilon$
3. Supplier capacity $Q_k \le K_s + \epsilon$
4. Minimum inventory target $I \ge I_{\min} - \epsilon$
5. Delivery delay $\Delta d \le \text{maximum\_acceptable\_delay\_days} + \epsilon$

If all three options fail constraints or have insufficient data, the engine fails closed:
- `recommended_option_id = null`
- `recommendation_status = "NO_FEASIBLE_OPTION"`

---

## 4. API Endpoints & Request/Response Samples

### POST `/api/optimization/alternatives`

**Request:**
```json
{
  "shipment_id": "SHIP001",
  "scenario_overrides": {
    "budget": {
      "max_total_cost": 50000.0
    },
    "delivery": {
      "maximum_acceptable_delay_days": 7.0
    }
  },
  "save_to_database": false
}
```

**Response:**
```json
{
  "shipment_id": "SHIP001",
  "scenario_id": "baseline_supply_chain",
  "baseline": {
    "shipment_id": "SHIP001",
    "product_id": "PROD001",
    "product_name": "Industrial Micro-Controller",
    "supplier_id": "SUP001",
    "supplier_name": "Alpha Manufacturing",
    "transport_mode": "Road",
    "quantity": 100.0,
    "unit_cost": 50.0,
    "shipping_cost": 250.0,
    "estimated_total_cost": 5250.0,
    "predicted_delay_probability": 0.85,
    "predicted_delay_days": 8.0,
    "risk_level": "HIGH",
    "planned_lead_time_days": 5.0,
    "total_delivery_days": 13.0,
    "currency": "USD"
  },
  "alternatives": [
    {
      "option_id": "A",
      "name": "Air Freight",
      "feasibility": "FEASIBLE",
      "estimated_total_cost": 6500.0,
      "additional_cost": 1250.0,
      "additional_cost_percentage": 23.81,
      "estimated_delivery_days": 2.5,
      "schedule_impact_days": -10.5,
      "delay_probability": 0.12,
      "predicted_delay_days": 0.5,
      "risk_level": "LOW",
      "objective_value": 6515.0,
      "supplier_id": "SUP001",
      "supplier_name": "Alpha Manufacturing",
      "transport_mode": "Air",
      "cost_breakdown": {
        "procurement_cost": 5000.0,
        "shipping_cost": 1500.0,
        "delay_cost": 15.0,
        "risk_cost": 0.0
      },
      "constraint_violations": [],
      "assumptions": [
        "Air freight rate: $0.35/km/100-units across 1000 km corridor",
        "Air transit modal lead time: 2.0 days"
      ],
      "explanation": "Expediting via Air Freight cuts transit lead time from 5.0 to 2.0 days and lowers predicted delay to 0.5 days.",
      "is_recommended": true
    },
    {
      "option_id": "B",
      "name": "Secondary Supplier",
      "feasibility": "FEASIBLE",
      "estimated_total_cost": 5750.0,
      "additional_cost": 500.0,
      "additional_cost_percentage": 9.52,
      "estimated_delivery_days": 7.2,
      "schedule_impact_days": -5.8,
      "delay_probability": 0.22,
      "predicted_delay_days": 1.2,
      "risk_level": "LOW",
      "objective_value": 5756.6,
      "supplier_id": "SUP002",
      "supplier_name": "Beta Electro-Hub",
      "transport_mode": "Road",
      "is_recommended": false
    },
    {
      "option_id": "C",
      "name": "Delay Product Launch",
      "feasibility": "INSUFFICIENT_DATA",
      "estimated_total_cost": 5250.0,
      "additional_cost": 0.0,
      "schedule_impact_days": 8.0,
      "delay_probability": 0.85,
      "predicted_delay_days": 8.0,
      "risk_level": "HIGH",
      "is_recommended": false
    }
  ],
  "recommended_option_id": "B",
  "recommendation_status": "FEASIBLE_RECOMMENDATION",
  "recommendation_reason": "Option B (Secondary Supplier) is recommended with optimal Day 12 objective cost $5,756.60...",
  "trade_off_analysis": "• Option A (Air Freight) [FEASIBLE]: Cost=$6,500.00 (+23.8%), Delivery=2.5 days...\n• Option B (Secondary Supplier) [FEASIBLE]: Cost=$5,750.00 (+9.5%), Delivery=7.2 days...",
  "model_version": "v1.0",
  "warnings": [],
  "evaluated_at": "2026-10-18T10:00:00Z"
}
```

---

## 5. Automated Test Execution

All alternative generation and evaluation logic is covered by deterministic automated tests:

```bash
# Run Day 13 Prescriptive Alternatives tests
backend/.venv/bin/pytest optimization/tests/test_alternatives.py \
                         optimization/tests/test_alternative_evaluator.py \
                         optimization/tests/test_decision_ranker.py \
                         tests/api/test_optimization_alternatives.py -v

# Run frontend vitest test suite
npm --prefix frontend test
```
