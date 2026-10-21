# SupplyPrescript — Optimization API Specification (Day 14)
**Phase 4:** Prescriptive Optimization  
**Endpoint:** `POST /api/optimize`  
**Router Module:** [`backend/app/api/routes/optimization.py`](file:///Users/sujal/Desktop/SupplyPrescript/backend/app/api/routes/optimization.py)  
**Schema Definitions:** [`optimization/decision_schemas.py`](file:///Users/sujal/Desktop/SupplyPrescript/optimization/decision_schemas.py)

---

## 1. Executive Summary & Purpose

The `POST /api/optimize` endpoint serves as the production-grade prescriptive optimization interface for SupplyPrescript. When a shipment experiences high delay risk or operational disruption, this endpoint coordinates:
1. Direct feature retrieval from PostgreSQL for authoritative operational parameters (quantities, supplier metrics, inventory levels, freight costs).
2. Direct inference using active registered ML models (`v1.0 XGBoost`) without recursive HTTP calls or data leakage.
3. Formulation and evaluation of 3 distinct supply-chain decision strategies:
   - **Option A (Air Freight):** Rapid transit speedup (0.4× transit duration), premium freight multiplier.
   - **Option B (Secondary Supplier):** Alternate pre-qualified supplier routing, independent lead time and capacity.
   - **Option C (Delay Product Launch):** Schedule buffer extension, zero expediting premium, holding cost accrual.
4. Mathematical constraint auditing against hard business constraints (budget ceiling, supplier capacity, minimum inventory, delivery delay tolerance).
5. Multi-criteria ranking using the Day 12 objective function ($\min Z = C_{\text{total}} + C_{\text{delay}} + C_{\text{risk}}$).
6. Fail-closed recommendation gating returning structured feasibility, slack margins, and decision rationale.

---

## 2. API Endpoint Specification

### `POST /api/optimize`

- **Tags:** `Optimization`
- **Content-Type:** `application/json`
- **Authentication:** Inherits application security configuration.
- **Summary:** Prescriptive Supply-Chain Optimization & Alternative Recommendation.

### Request Payload (`OptimizationRequest`)

| Field | Type | Required | Default | Validation / Constraints | Description |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `shipment_id` | `string` | **Yes** | — | Non-empty string (`min_length=1`) | Target shipment identifier (e.g., `"SHP1023"`, `"SHIP001"`). |
| `scenario_id` | `string` | No | `"baseline"` | Must be one of `SUPPORTED_SCENARIOS` | Prescriptive planning scenario. Options: `baseline`, `budget_constrained`, `delay_sensitive`, `risk_averse`, `expedited_service`, `inventory_buffering`. |
| `num_options` | `integer` | No | `3` | $1 \leq \text{num\_options} \leq 10$ | Maximum number of ranked candidate decisions to return. |
| `scenario_overrides` | `object` | No | `null` | Valid JSON dictionary | Optional runtime overrides for budget limits, unit penalties, or tolerances. |

#### Request Example

```json
{
  "shipment_id": "SHP1023",
  "scenario_id": "baseline",
  "num_options": 3
}
```

---

## 3. End-to-End Processing Architecture

```text
POST /api/optimize
       │
       ▼
[ Step 1: Request Validation ]
  ├── Check shipment_id non-blank (400 if empty)
  ├── Validate scenario_id in SUPPORTED_SCENARIOS (400 if invalid)
  └── Validate num_options in [1, 10] (422 via Pydantic)
       │
       ▼
[ Step 2: Database Retrieval ]
  ├── Resolve authoritative Shipment from PostgreSQL (404 if missing)
  ├── Join Product, Supplier, and Inventory state
  └── Ensure no N+1 queries through targeted single-row reads
       │
       ▼
[ Step 3: Direct ML Inference ]
  ├── Load active v1.0 XGBoost models directly via predict_shipment()
  ├── Calculate delay_probability and predicted_delay_days
  └── Classify categorical risk level (LOW, MEDIUM, HIGH)
       │
       ▼
[ Step 4: Alternative Generation ]
  ├── Option A: Expedite via Air Freight (lead_time * 0.4, air freight surcharge)
  ├── Option B: Secondary Supplier allocation (query qualified backup suppliers)
  └── Option C: Delay Product Launch (absorb lead time, no freight surcharge)
       │
       ▼
[ Step 5: Hard Constraint Auditing & Objective Evaluation ]
  ├── Budget Constraint: Cost(option) <= max_total_cost ($50,000 USD baseline)
  ├── Supplier Capacity: Quantity <= supplier_capacity
  ├── Delivery Tolerance: Predicted Delay <= maximum_acceptable_delay_days
  └── Inventory Requirement: Ending Inventory >= min_safety_stock
  └── Calculate Day 12 Objective: Z = C_total + C_delay + C_risk
       │
       ▼
[ Step 6: Multi-Criteria Ranking & Fail-Closed Gating ]
  ├── Filter candidate options by is_recommendation_eligible
  ├── Sort feasible candidates ascending by objective score Z
  ├── If no options pass hard constraints:
  │     status = "NO_FEASIBLE_OPTION", recommended_option_id = null
  └── If feasible winner exists:
        status = "SUCCESS", recommended_option_id = winning option ID
       │
       ▼
[ Step 7: Response Assembly ]
  └── Return OptimizationResponse with telemetry, slacks, and explanations
```

---

## 4. Response Payloads & Status Codes

### Response Model (`OptimizationResponse`)

| Field | Type | Description |
| :--- | :--- | :--- |
| `shipment_id` | `string` | Target shipment identifier evaluated. |
| `status` | `string` | Overall status: `SUCCESS`, `NO_FEASIBLE_OPTION`, `INSUFFICIENT_DATA`, `ERROR`. |
| `prediction` | `OptimizationPredictionSummary` | Delay probability, predicted delay days, categorical risk level, ML version. |
| `options` | `List[OptimizationOption]` | Ranked candidate options (at most `num_options`). |
| `recommended_option_id` | `string` or `null` | Identifier of winning option (`"A"`, `"B"`, `"C"`) or `null` if none feasible. |
| `recommendation_reason` | `string` | Business rationale for winning recommendation or root-cause failure breakdown. |
| `constraint_checks` | `List[OptimizationConstraintCheck]` | Itemized audit checks for Budget, Delivery Delay, and Supplier Capacity with slack values. |
| `warnings` | `List[string]` | Non-fatal audit alerts, assumptions, or missing secondary data notices. |
| `optimization_metadata` | `OptimizationMetadata` | Applied scenario, solver status, runtime in milliseconds, active model version. |

---

### Example 1: Feasible Recommendation (`SUCCESS`)

```json
{
  "shipment_id": "SHP1023",
  "status": "SUCCESS",
  "prediction": {
    "delay_probability": 0.82,
    "predicted_delay_days": 8.0,
    "risk_level": "HIGH",
    "model_version": "v1.0"
  },
  "options": [
    {
      "option_id": "A",
      "strategy": "AIR_FREIGHT",
      "name": "Expedite using air freight",
      "status": "FEASIBLE",
      "estimated_total_cost": 6500.0,
      "additional_cost": 1250.0,
      "estimated_delivery_days": 2.5,
      "delay_probability": 0.12,
      "risk_level": "LOW",
      "objective_value": 6515.0,
      "constraint_violations": [],
      "assumptions": [
        "Air freight transit speedup factor: 0.40x",
        "Air freight cost rate: $2.50 per kg/unit"
      ],
      "explanation": "Expediting via Air Freight eliminates ground delay risk, reducing transit time to 2.5 days with an incremental freight cost of $1,250.00.",
      "is_recommended": true
    },
    {
      "option_id": "B",
      "strategy": "SECONDARY_SUPPLIER",
      "name": "Switch to a qualified secondary supplier",
      "status": "FEASIBLE",
      "estimated_total_cost": 6800.0,
      "additional_cost": 1550.0,
      "estimated_delivery_days": 4.0,
      "delay_probability": 0.20,
      "risk_level": "LOW",
      "objective_value": 6840.0,
      "constraint_violations": [],
      "assumptions": [
        "Secondary supplier capacity: 500 units",
        "Unit price premium: +$2.50/unit"
      ],
      "explanation": "Reroutes procurement to vetted backup supplier 'Apex Industrial' in Pune with 94% on-time historical reliability.",
      "is_recommended": false
    },
    {
      "option_id": "C",
      "strategy": "DELAY_LAUNCH",
      "name": "Delay the product launch",
      "status": "FEASIBLE",
      "estimated_total_cost": 5250.0,
      "additional_cost": 0.0,
      "estimated_delivery_days": 13.0,
      "delay_probability": 0.82,
      "risk_level": "HIGH",
      "objective_value": 7250.0,
      "constraint_violations": [],
      "assumptions": [
        "Launch date shifted by 8.0 days",
        "Holding cost accrued at $0.05/unit/day"
      ],
      "explanation": "Accepts predicted delay of 8.0 days without expediting costs; incurs delay risk penalty of $2,000.00 in Day 12 objective.",
      "is_recommended": false
    }
  ],
  "recommended_option_id": "A",
  "recommendation_reason": "Option A recommended with optimal Day 12 objective cost $6,515.00.",
  "constraint_checks": [
    {
      "name": "Maximum Budget",
      "status": "SATISFIED",
      "lhs_value": 6500.0,
      "rhs_value": 50000.0,
      "slack": 43500.0,
      "description": "Applicable expenditure $6,500.00 checked against $50,000.00 ceiling."
    },
    {
      "name": "Delivery Delay Tolerance",
      "status": "SATISFIED",
      "lhs_value": 0.0,
      "rhs_value": 7.0,
      "slack": 7.0,
      "description": "Predicted delay 0.0 days checked against 7.0 days tolerance."
    },
    {
      "name": "Supplier Capacity",
      "status": "SATISFIED",
      "lhs_value": 100.0,
      "rhs_value": 5000.0,
      "slack": 4900.0,
      "description": "Order quantity 100 units checked against 5,000 units capacity."
    }
  ],
  "warnings": [],
  "optimization_metadata": {
    "scenario_id": "baseline",
    "solver_status": "OPTIMAL",
    "runtime_ms": 16.4,
    "model_version": "v1.0"
  }
}
```

---

### Example 2: Infeasible / Constraint Violation (`NO_FEASIBLE_OPTION`)

When hard constraints (e.g., restrictive budget ceiling or strict delivery tolerance) eliminate all candidate options, the endpoint **fails closed** rather than recommending an invalid plan:

```json
{
  "shipment_id": "SHP1023",
  "status": "NO_FEASIBLE_OPTION",
  "prediction": {
    "delay_probability": 0.82,
    "predicted_delay_days": 8.0,
    "risk_level": "HIGH",
    "model_version": "v1.0"
  },
  "options": [
    {
      "option_id": "A",
      "strategy": "AIR_FREIGHT",
      "name": "Expedite using air freight",
      "status": "INFEASIBLE",
      "estimated_total_cost": 6500.0,
      "additional_cost": 1250.0,
      "estimated_delivery_days": 2.5,
      "delay_probability": 0.12,
      "risk_level": "LOW",
      "objective_value": 6515.0,
      "constraint_violations": [
        {
          "constraint_name": "Budget",
          "limit_value": 2000.0,
          "actual_value": 6500.0,
          "violation_amount": 4500.0,
          "message": "Option cost $6,500.00 exceeds scenario budget limit of $2,000.00."
        }
      ],
      "assumptions": ["Air speedup 0.4x"],
      "explanation": "Expediting via Air exceeds budget limit by $4,500.00.",
      "is_recommended": false
    },
    {
      "option_id": "B",
      "strategy": "SECONDARY_SUPPLIER",
      "name": "Switch to a qualified secondary supplier",
      "status": "INFEASIBLE",
      "estimated_total_cost": 6800.0,
      "additional_cost": 1550.0,
      "estimated_delivery_days": 4.0,
      "delay_probability": 0.20,
      "risk_level": "LOW",
      "objective_value": 6840.0,
      "constraint_violations": [
        {
          "constraint_name": "Budget",
          "limit_value": 2000.0,
          "actual_value": 6800.0,
          "violation_amount": 4800.0,
          "message": "Option cost $6,800.00 exceeds scenario budget limit of $2,000.00."
        }
      ],
      "assumptions": ["Secondary capacity 500 units"],
      "explanation": "Secondary supplier cost exceeds budget limit by $4,800.00.",
      "is_recommended": false
    },
    {
      "option_id": "C",
      "strategy": "DELAY_LAUNCH",
      "name": "Delay the product launch",
      "status": "INFEASIBLE",
      "estimated_total_cost": 5250.0,
      "additional_cost": 0.0,
      "estimated_delivery_days": 13.0,
      "delay_probability": 0.82,
      "risk_level": "HIGH",
      "objective_value": 7250.0,
      "constraint_violations": [
        {
          "constraint_name": "Budget",
          "limit_value": 2000.0,
          "actual_value": 5250.0,
          "violation_amount": 3250.0,
          "message": "Option cost $5,250.00 exceeds scenario budget limit of $2,000.00."
        }
      ],
      "assumptions": ["Launch date shifted 8.0 days"],
      "explanation": "Delaying launch exceeds budget limit by $3,250.00.",
      "is_recommended": false
    }
  ],
  "recommended_option_id": null,
  "recommendation_reason": "No candidate alternative satisfies all hard business constraints under the 'budget_constrained' scenario.",
  "constraint_checks": [
    {
      "name": "Maximum Budget",
      "status": "VIOLATED",
      "lhs_value": 5250.0,
      "rhs_value": 2000.0,
      "slack": -3250.0,
      "description": "Applicable expenditure $5,250.00 checked against $2,000.00 ceiling."
    },
    {
      "name": "Delivery Delay Tolerance",
      "status": "SATISFIED",
      "lhs_value": 8.0,
      "rhs_value": 14.0,
      "slack": 6.0,
      "description": "Predicted delay 8.0 days checked against 14.0 days tolerance."
    },
    {
      "name": "Supplier Capacity",
      "status": "SATISFIED",
      "lhs_value": 100.0,
      "rhs_value": 5000.0,
      "slack": 4900.0,
      "description": "Order quantity 100 units checked against 5,000 units capacity."
    }
  ],
  "warnings": [
    "Hard constraint violation: Budget ceiling exceeded by all candidate options."
  ],
  "optimization_metadata": {
    "scenario_id": "budget_constrained",
    "solver_status": "INFEASIBLE",
    "runtime_ms": 12.8,
    "model_version": "v1.0"
  }
}
```

---

## 5. HTTP Error Status Codes

The endpoint strictly adheres to HTTP status code conventions:

| HTTP Status | Trigger Condition | Response Body Format |
| :--- | :--- | :--- |
| **400 Bad Request** | Blank `shipment_id`, whitespace-only identifier, or unsupported `scenario_id`. | `{"detail": "Unsupported scenario_id 'invalid_scenario'. Supported scenarios are: ['baseline', ...]"}` |
| **404 Not Found** | Shipment identifier does not exist in the PostgreSQL `shipments` table. | `{"detail": "Shipment with ID 'NON_EXISTENT' was not found in the database."}` |
| **422 Unprocessable Entity** | `num_options` is less than 1 or greater than 10, or JSON body is malformed. | Fast-fail Pydantic validation error schema. |
| **500 Internal Server Error** | Unexpected database disconnect or unhandled runtime mathematical error. | `{"detail": "Prescriptive optimization processing failure: <details>"}` |
| **503 Service Unavailable** | Registered ML model artifacts (`v1.0 XGBoost`) are missing from disk or corrupt. | `{"detail": "Predictive ML model artifacts are unavailable: <details>"}` |

---

## 6. Supported Scenarios

The engine supports 7 operational scenario templates defined in [`optimization/scenarios.py`](file:///Users/sujal/Desktop/SupplyPrescript/optimization/scenarios.py):

1. **`baseline` / `baseline_supply_chain`:** Balanced weights ($w_{\text{cost}} = 1.0, w_{\text{delay}} = 100, w_{\text{risk}} = 500$), standard budget ceiling ($50,000 USD).
2. **`budget_constrained`:** Stringent budget limit ($30,000 USD), prioritizes minimal incremental expense ($w_{\text{cost}} = 1.5$).
3. **`delay_sensitive`:** High penalty on arrival latency ($w_{\text{delay}} = 250$), strict 3-day delay tolerance ceiling.
4. **`risk_averse`:** High penalty on disruption probabilities ($w_{\text{risk}} = 1200$), strongly prefers established suppliers and expedited modes.
5. **`expedited_service`:** Optimized for fastest transit times, accepts premium freight multipliers.
6. **`inventory_buffering`:** Enforces higher buffer stock to mitigate upstream supplier variance.

---

## 7. Verification & Automated Test Suite

### Running Pytest Test Suite

Execute the dedicated test suite for the optimization API and hard constraint enforcement:

```bash
# Test the Day 14 Production Optimization API
backend/.venv/bin/pytest optimization/tests/test_optimization_api.py -v

# Test Hard Business Constraints (Budget, Capacity, Inventory, Delivery)
backend/.venv/bin/pytest optimization/tests/test_budget_constraint.py \
                         optimization/tests/test_supplier_capacity.py \
                         optimization/tests/test_inventory_constraint.py \
                         optimization/tests/test_delivery_constraint.py \
                         optimization/tests/test_solution_validation.py \
                         optimization/tests/test_recommendation_safety.py \
                         optimization/tests/test_adversarial_cases.py -v

# Run the complete test suite (309 tests)
backend/.venv/bin/pytest
```

### Running Frontend Tests (Vitest)

```bash
npm --prefix frontend test -- --run
```

---

## 8. Example cURL Invocations

### Standard Baseline Optimization
```bash
curl -X POST "http://localhost:8000/api/optimize" \
     -H "Content-Type: application/json" \
     -d '{
       "shipment_id": "SHIP001",
       "scenario_id": "baseline",
       "num_options": 3
     }'
```

### Strict Budget Constrained Optimization with Runtime Overrides
```bash
curl -X POST "http://localhost:8000/api/optimize" \
     -H "Content-Type: application/json" \
     -d '{
       "shipment_id": "SHIP001",
       "scenario_id": "budget_constrained",
       "num_options": 3,
       "scenario_overrides": {
         "budget": {
           "max_total_cost": 25000.0
         }
       }
     }'
```

---

*Authored for SupplyPrescript Phase 4 — Prescriptive Optimization Engine.*
