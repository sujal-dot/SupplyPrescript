# SupplyPrescript — Day 21: Feedback / Decision ROI Dashboard

**Phase:** 6 — Closed-Loop Analytics  
**Date:** October 24, 2026  
**Status:** Implemented and Verified  

---

## 1. Executive Summary

The **Decision ROI Dashboard** completes SupplyPrescript's closed-loop analytics cycle by synthesizing persisted prescriptive decisions and verified operational execution outcomes. It provides business leaders and operations managers with an audit-grade intelligence interface to evaluate recommendation success, model prediction accuracy, financial cost differences, forecast variance versus verified baseline savings, and return on investment grouped by operational strategy.

Every metric, distribution, and KPI rendered across the dashboard is derived deterministically from PostgreSQL records (`decisions`, `outcomes`, and `shipments`) or backend analytical pipelines.

---

## 2. Core Architecture & Endpoints

### Analytical Backend Endpoint

- **Route:** `GET /api/analytics/decision-roi`
- **Controller:** [`backend/app/api/routes/analytics.py`](file:///Users/sujal/Desktop/SupplyPrescript/backend/app/api/routes/analytics.py)
- **Calculation Engine:** [`backend/app/services/decision_roi.py`](file:///Users/sujal/Desktop/SupplyPrescript/backend/app/services/decision_roi.py)
- **Response Schema:** [`DecisionROIDashboardResponse`](file:///Users/sujal/Desktop/SupplyPrescript/backend/app/schemas/roi.py)

#### Supported Query Filters

| Parameter | Type | Description |
| :--- | :--- | :--- |
| `strategy` | `string` | Filter by operational strategy (e.g., `AIR_FREIGHT`, `SECONDARY_SUPPLIER`, `EXPEDITE`) |
| `decision_status` | `string` | Filter by operational status (`RECORDED`) or evaluation classification (`SUCCESS`, `PARTIAL_SUCCESS`, `FAILURE`, `PENDING_REVIEW`) |
| `start_date` | `ISO datetime` | Filter decisions created on or after this timestamp |
| `end_date` | `ISO datetime` | Filter decisions created on or before this timestamp |
| `currency` | `string` | Isolate financial metrics to comparable currencies (default: `USD`) |
| `shipment_id` | `string` | Search and isolate decisions targeting a specific shipment |
| `supplier` | `string` | Filter by assigned or fulfilling supplier identifier |
| `page` / `page_size` | `int` | Server-side pagination parameters for decision audit records |

---

## 3. Mathematical & Accounting Principles

### A. Non-Distorting Success Rate Denominators

A fundamental closed-loop analytics rule is that pending decisions (awaiting operational delivery or invoice actuals) must **never** be counted as failures or included in the success rate denominator.

$$\text{Eligible Completed Decisions} = \text{Successful} + \text{Partially Successful} + \text{Failed}$$

$$\text{Success Rate} = \left( \frac{\text{Successful Decisions}}{\text{Eligible Completed Decisions}} \right) \times 100$$

$$\text{Failure Rate} = \left( \frac{\text{Failed Decisions}}{\text{Eligible Completed Decisions}} \right) \times 100$$

- Decisions with `PENDING_REVIEW` are reported prominently in their own card and breakdown category, but strictly excluded from the rate denominator.

### B. Prediction Accuracy & Error Metrics

Evaluates how accurately the ML models predicted costs and delivery delays against verified actuals:

1. **Cost Mean Absolute Error (MAE):**
   $$\text{MAE}_{\text{cost}} = \frac{1}{N} \sum_{i=1}^{N} |\text{actual\_cost}_i - \text{predicted\_cost}_i|$$
2. **Cost Mean Absolute Percentage Error (MAPE):**
   $$\text{MAPE}_{\text{cost}} = \frac{1}{M} \sum_{j=1}^{M} \left( \frac{|\text{actual\_cost}_j - \text{predicted\_cost}_j|}{\text{actual\_cost}_j} \right) \times 100 \quad (\text{for } \text{actual\_cost}_j > 0)$$
3. **Cost Root Mean Squared Error (RMSE):**
   $$\text{RMSE}_{\text{cost}} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (\text{actual\_cost}_i - \text{predicted\_cost}_i)^2}$$
4. **Cost Directional Bias (Mean Signed Error):**
   $$\text{MSError}_{\text{cost}} = \frac{1}{N} \sum_{i=1}^{N} (\text{actual\_cost}_i - \text{predicted\_cost}_i)$$
5. **Delay Mean Absolute Error (MAE):**
   $$\text{MAE}_{\text{delay}} = \frac{1}{K} \sum_{k=1}^{K} |\text{actual\_delay}_k - \text{predicted\_delay}_k|$$
6. **Delay Directional Bias (Mean Signed Error):**
   $$\text{MSError}_{\text{delay}} = \frac{1}{K} \sum_{k=1}^{K} (\text{actual\_delay}_k - \text{predicted\_delay}_k)$$

### C. Forecast Variance vs. Verified Baseline Savings

The dashboard enforces transparent separation between forecast variance and causal baseline savings:

- **Forecast Variance:**
  $$\text{Forecast Variance} = \text{predicted\_cost} - \text{actual\_cost}$$
  Measures execution performance relative to the prescriptive recommendation's forecast. Positive means actual costs were under budget.
- **Verified Baseline Savings:**
  $$\text{Baseline Savings} = \text{baseline\_cost} - \text{actual\_cost}$$
  Where $\text{baseline\_cost} = (\text{quantity} \times \text{unit\_cost}) + \text{shipping\_cost}$. Measures true economic savings against the unmitigated operational baseline.

### D. Weighted Strategy ROI

$$\text{Strategy ROI} = \left( \frac{\sum \text{net\_benefit}}{\sum \text{investment\_cost}} \right) \times 100$$

- Calculated only when documented, positive incremental investment outlays are recorded.
- When investment base is unavailable, marked clearly as `N/A (Denominator Pending)` rather than fabricated.

---

## 4. Frontend Component Hierarchy

The React dashboard is mounted at `/decision-roi` and integrated into the primary sidebar navigation:

```text
frontend/src/
├── pages/
│   └── DecisionROI.jsx                     # Top-level page container, state management, modal integration
├── components/roi/
│   ├── ROIFilters.jsx                      # Filter bar with date presets, strategy, outcome status, currency
│   ├── ROISummaryCards.jsx                 # 8 top-level KPI cards with rates and transparency subtexts
│   ├── DecisionSuccessChart.jsx            # Donut chart of success distribution with centered rate
│   ├── CostDifferenceChart.jsx             # Bar chart of actual - predicted cost by strategy
│   ├── PredictionAccuracyChart.jsx         # Cost & delay error cards (MAE, MAPE, RMSE, signed bias)
│   ├── SavingsChart.jsx                    # Cumulative Area chart comparing forecast variance vs baseline savings
│   ├── ROIByStrategyChart.jsx              # Strategy ROI bar chart with denominator disclosures
│   ├── DecisionPerformanceTable.jsx       # Paginated decision audit table with search and modal link
│   └── DecisionSuccessBadge.jsx            # Standardized outcome status pill
└── services/
    └── roiService.js                       # API client wrapper for /api/analytics/decision-roi
```

---

## 5. Verification & Test Coverage

- **Backend Integration Tests:** [`tests/api/test_analytics_dashboard_api.py`](file:///Users/sujal/Desktop/SupplyPrescript/tests/api/test_analytics_dashboard_api.py) (8 tests passing)
- **Frontend Dashboard Tests:** [`frontend/src/__tests__/DecisionROIDashboard.test.jsx`](file:///Users/sujal/Desktop/SupplyPrescript/frontend/src/__tests__/DecisionROIDashboard.test.jsx) (10 tests passing)
- **Full Backend Suite:** 252 tests passing (`pytest tests/`)
- **Full Frontend Suite:** 53 tests passing across 15 test files (`vitest run`)
- **Production Build:** Vite bundle built successfully without errors.
