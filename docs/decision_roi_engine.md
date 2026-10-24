# SupplyPrescript — Day 20: Decision ROI Engine Documentation

**Phase:** 6 — Closed-Loop Analytics  
**Date:** October 23, 2026  
**Version:** 1.0  
**Status:** Implemented & Verified  

---

## 1. Overview & Architectural Principles

The **SupplyPrescript Decision ROI Engine** provides a verified, mathematically sound analytical framework that closes the loop between prescriptive decision optimization (Days 15–18) and operational actuals recorded in PostgreSQL (Day 19).

### Core Architectural Principles

1. **Immutable Historical Prescriptions**: Predictions (`predicted_cost`, `predicted_delay`) are retrieved strictly from the immutable snapshot saved when the decision was executed and authorized in PostgreSQL. New machine learning or MIP optimization solutions are never substituted retroactively.
2. **Empirical Actuals**: Actual costs, actual delivery milestones, and actual fulfillment quantities are fetched directly from the Day 19 `outcomes` table.
3. **Causal Rigor & Separation of Concerns**:
   - **Prediction Variance**: Actual result versus the original prediction (`actual_cost - predicted_cost`).
   - **Money Saved vs Forecast**: Forecast difference (`predicted_cost - actual_cost`), indicating budget variance, not causal savings.
   - **Baseline Savings**: Actual outcome versus a verified baseline plan (`baseline_cost - actual_cost`). Only computed when a documented, comparable baseline exists for the same shipment, quantity, service tier, and currency.
   - **Return on Investment (ROI)**: Net benefit relative to a documented, positive incremental investment denominator (`(net_benefit / investment_cost) * 100`). If no valid investment denominator exists, ROI is explicitly returned as `UNAVAILABLE` rather than inventing an arbitrary metric.
4. **No Value Fabrication**: Missing values are returned as `null` / `None` with transparent explanations; missing data is never coerced to zero.
5. **Deterministic Calculation**: Calculations are reproducible and tagged with `calculation_version: "1.0"`.

---

## 2. Mathematical Definitions & Sign Conventions

### A. Cost Difference

$$\text{cost\_difference} = \text{actual\_cost} - \text{predicted\_cost}$$

- **Positive ($> 0$)**: Actual expenditure exceeded the prediction (Cost Overrun).
- **Negative ($< 0$)**: Actual expenditure was below the prediction (Under Budget).
- **Zero ($= 0$)**: Actual expenditure matched the forecast exactly.

*Illustrative Example:*
- Predicted Cost: \$15,000.00
- Actual Cost: \$18,000.00
- $\text{cost\_difference} = \$18,000.00 - \$15,000.00 = +\$3,000.00$ (Overrun of \$3,000.00).

---

### B. Money Saved Metrics

#### 1. Money Saved vs Prediction (Forecast Variance)

$$\text{money\_saved\_vs\_prediction} = \text{predicted\_cost} - \text{actual\_cost}$$

- **Positive ($> 0$)**: Favorable budget variance (cost came in below the predicted cap).
- **Negative ($< 0$)**: Unfavorable budget variance (cost overrun).
- *Caveat*: This is an internal forecast variance metric, not causal proof of real-world monetary savings.

#### 2. Money Saved vs Baseline (Verified Savings)

$$\text{money\_saved\_vs\_baseline} = \text{baseline\_cost} - \text{actual\_cost}$$

- **Calculated only when**: A documented baseline shipment exists with `quantity`, `unit_cost`, `shipping_cost`, and identical currency.
  $$\text{baseline\_cost} = (\text{quantity} \times \text{unit\_cost}) + \text{shipping\_cost}$$
- If no baseline is available, this metric evaluates to `null`.
- Never presents savings against an undocumented alternative as verified savings.

---

### C. Cost Variance Percentage

$$\text{cost\_variance\_percentage} = \left(\frac{\text{actual\_cost} - \text{predicted\_cost}}{\text{predicted\_cost}}\right) \times 100$$

- If $\text{predicted\_cost} \le 0$ or missing: Returns `null` with an explanatory note (`"Predicted cost is zero or missing; percentage variance is mathematically undefined."`).

---

### D. Delay Difference

$$\text{delay\_difference} = \text{actual\_delay} - \text{predicted\_delay}$$

- **Positive ($> 0$)**: Delivery delay was worse (longer) than predicted.
- **Negative ($< 0$)**: Delivery delay was lower (earlier) than predicted.
- **Zero ($= 0$)**: Delivery matched forecast schedule exactly.
- *Milestone Definition*: Compares schedule delay in days against agreed baseline, distinct from total transit duration.

---

### E. Return on Investment (ROI)

$$\text{net\_benefit} = \text{baseline\_cost} - \text{actual\_cost} - \text{additional\_decision\_costs}$$

$$\text{ROI\_percentage} = \left(\frac{\text{net\_benefit}}{\text{investment\_cost}}\right) \times 100$$

Where:
- $\text{investment\_cost}$ is a documented, positive monetary denominator representing the incremental capital outlay or surcharge invested to execute the decision over baseline:
  - Default derivation: When $\text{predicted\_cost} > \text{baseline\_cost}$, the planned incremental investment is $\text{predicted\_cost} - \text{baseline\_cost}$.
  - Explicit override: Passed via query parameter `investment_cost` when dedicated capital or setup fees are audited.
- **Unavailable Denominator Rule**: If baseline cost is missing, actual cost is missing, currencies mismatch, or $\text{investment\_cost} \le 0$, the engine returns:
  ```json
  "roi": {
    "investment_cost": null,
    "net_benefit": null,
    "roi_percentage": null,
    "status": "UNAVAILABLE",
    "reason": "A valid baseline and investment-cost definition are not available."
  }
  ```

#### Portfolio Weighted Aggregate ROI

Portfolio ROI is calculated across all comparable completed decisions using total sums:

$$\text{Portfolio ROI} = \left(\frac{\sum \text{net\_benefit}_i}{\sum \text{investment\_cost}_i}\right) \times 100$$

The engine strictly rejects averaging individual percentage ROIs to prevent unweighted ratio distortion.

---

## 3. Decision Success Evaluation Framework

The engine independently evaluates five dimensions under a configurable policy (`DecisionSuccessPolicy`):

### Evaluation Dimensions

1. **Cost Performance**:
   - `BETTER_THAN_PREDICTED`: $\text{actual\_cost} < \text{predicted\_cost} - \text{tolerance}$
   - `ON_TARGET`: $|\text{actual\_cost} - \text{predicted\_cost}| \le \text{tolerance}$
   - `WORSE_THAN_PREDICTED`: $\text{actual\_cost} > \text{predicted\_cost} + \text{tolerance}$
   - `UNKNOWN`: Missing actual or predicted cost.

2. **Delivery Performance**:
   - `BETTER_THAN_PREDICTED`: $\text{actual\_delay} < \text{predicted\_delay} - \text{tolerance}$
   - `ON_TARGET`: $|\text{actual\_delay} - \text{predicted\_delay}| \le \text{tolerance}$
   - `WORSE_THAN_PREDICTED`: $\text{actual\_delay} > \text{predicted\_delay} + \text{tolerance}$
   - `UNKNOWN`: Missing actual or predicted delay.

3. **Constraint Compliance**:
   - `PASS`: All hard constraints verified during decision write-back passed.
   - `FAIL`: Any hard constraint violated (e.g., budget ceiling breach, capacity overflow).
   - `UNKNOWN`: No constraint validation snapshot.

4. **Quantity Performance**:
   - `MET_TARGET`: Actual quantity equals planned quantity within tolerance.
   - `EXCEEDED_TARGET`: Actual quantity exceeds planned quantity.
   - `PARTIAL_FULFILLMENT`: Actual quantity > 0 but below target.
   - `BELOW_TARGET`: Actual quantity is 0 or negative.
   - `UNKNOWN`: Quantity records absent.

5. **Data Completeness**:
   - `COMPLETE`: Both cost and delivery delay records are finalized.
   - `PARTIAL`: Only one dimension is finalized.
   - `INSUFFICIENT`: Neither actual cost nor actual delay is recorded.

### Overall Status Rules

| Status | Condition |
|---|---|
| `SUCCESS` | Both cost and delivery performance are `BETTER_THAN_PREDICTED` or `ON_TARGET`, constraints `PASS`, and data is `COMPLETE`. |
| `PARTIAL_SUCCESS` | One dimension met/exceeded targets while the other had a controlled variance (e.g. delivery met target despite cost overrun), with an explicit explanation. |
| `FAILURE` | Mandatory constraint violation, or both cost and delivery performance failed predictions (`WORSE_THAN_PREDICTED`). |
| `PENDING_REVIEW` | Operational outcome is not recorded or is only partially finalized. Incomplete records are never assumed to have passed. |

---

## 4. REST API Specification

### 1. Single Decision ROI Endpoint

```http
GET /api/decisions/{decision_id}/roi
```

#### Query Parameters (Optional)
- `investment_cost` (`number`, optional): Documented incremental investment denominator override.
- `additional_decision_costs` (`number`, optional): Additional execution expenditures.

#### Sample 200 OK Response
```json
{
  "decision_id": "DEC-EXEC-101",
  "shipment_id": "SHIP000005",
  "currency": "USD",
  "cost": {
    "predicted_cost": "15000.00",
    "actual_cost": "18000.00",
    "cost_difference": "3000.00",
    "cost_variance_percentage": 20.0,
    "money_saved_vs_prediction": "-3000.00",
    "baseline_cost": "22000.00",
    "money_saved_vs_baseline": "4000.00"
  },
  "delivery": {
    "predicted_delay": 3.0,
    "actual_delay": 2.0,
    "delay_difference": -1.0
  },
  "roi": {
    "investment_cost": "2000.00",
    "net_benefit": "4000.00",
    "roi_percentage": 200.0,
    "status": "CALCULATED",
    "reason": "Calculated as (Net Benefit 4,000.00 USD / Incremental Investment 2,000.00 USD) * 100."
  },
  "decision_evaluation": {
    "decision_success": "PARTIAL_SUCCESS",
    "cost_performance": "WORSE_THAN_PREDICTED",
    "delivery_performance": "BETTER_THAN_PREDICTED",
    "constraint_compliance": "PASS",
    "quantity_performance": "MET_TARGET",
    "data_completeness": "COMPLETE",
    "success_reason": "Cost exceeded prediction while delivery was earlier than predicted or on target; critical schedule milestone met.",
    "policy_is_provisional": true
  },
  "calculation_version": "1.0",
  "calculation_method": "Cost difference = actual_cost - predicted_cost...",
  "notes": []
}
```

---

### 2. Portfolio-Level ROI Summary Endpoint

```http
GET /api/analytics/decision-roi
```

#### Query Parameters (Optional)
- `shipment_id` (`string`): Filter by shipment ID.
- `status` (`string`): Filter by decision status (e.g. `RECORDED`, `PENDING_REVIEW`).
- `supplier` (`string`): Filter by fulfilling supplier.
- `start_date` (`datetime`): Filter by starting timestamp.
- `end_date` (`datetime`): Filter by ending timestamp.
- `currency` (`string`, default: `"USD"`): Isolate currency to prevent distorted aggregation.

#### Sample 200 OK Response
```json
{
  "total_decisions": 25,
  "decisions_with_outcomes": 18,
  "decisions_pending_outcomes": 7,
  "currency": "USD",
  "total_predicted_cost": "320000.00",
  "total_actual_cost": "295000.00",
  "aggregate_cost_variance": "-25000.00",
  "aggregate_cost_variance_percentage": -7.81,
  "aggregate_money_saved_vs_prediction": "25000.00",
  "aggregate_baseline_savings": "48000.00",
  "success_counts": {
    "SUCCESS": 12,
    "PARTIAL_SUCCESS": 4,
    "FAILURE": 2,
    "PENDING_REVIEW": 7
  },
  "aggregate_roi": {
    "investment_cost": "30000.00",
    "net_benefit": "48000.00",
    "roi_percentage": 160.0,
    "status": "CALCULATED",
    "reason": "Portfolio ROI weighted across 18 completed decisions: (Total Net Benefit 48,000.00 USD / Total Investment 30,000.00 USD) * 100."
  },
  "excluded_incomplete_records_count": 7,
  "calculation_version": "1.0"
}
```

---

## 5. Frontend Dashboard Components

The ROI dashboard is integrated into the React Command Center and Decision Modal:

1. [`DecisionROISummary.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/DecisionROISummary.jsx): Top-level summary container featuring the decision header, success badge, reason card, 8 core cards, diagnostic grid, comparison table, and ROI formula breakdown.
2. [`DecisionROICards.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/DecisionROICards.jsx): Grid of 8 individual KPI cards with directional arrows, color coding, and accessible tags.
3. [`CostVarianceCard.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/CostVarianceCard.jsx): Specialized financial card clearly distinguishing money saved vs forecast from verified savings vs baseline.
4. [`DeliveryVarianceCard.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/DeliveryVarianceCard.jsx): Schedule delay variance card with clear sign convention.
5. [`ROIBreakdown.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/ROIBreakdown.jsx): Transparent return on investment card with denominator and policy explanation.
6. [`DecisionROITable.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/DecisionROITable.jsx): Side-by-side comparison table (Metric | Predicted | Actual | Difference) rendering only rows with verified data.
7. [`DecisionSuccessBadge.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/components/roi/DecisionSuccessBadge.jsx): Status pill representing `SUCCESS`, `PARTIAL_SUCCESS`, `FAILURE`, and `PENDING_REVIEW`.

---

## 6. Auditability & Known Limitations

### Auditability Guarantees
- Original decision predictions and optimization run IDs are immutable.
- Calculations are pure functions of persisted inputs and policy settings.
- All endpoints report `calculation_version`.

### Known Limitations & Day 21 Recommendations
1. **Dynamic Investment Denominator**: In complex multi-echelon interventions involving partial air freight and partial expediting, investment costs should be captured as an itemized line item during decision execution.
2. **Counterfactual Simulation**: Currently, baseline costs reflect master shipment planned values. Future phases may evaluate counterfactual carrier simulations under stochastic disruptions.
