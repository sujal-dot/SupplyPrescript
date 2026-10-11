# SupplyPrescript — Phase 3: Predictive ML Engine

This directory contains the machine-learning pipeline, feature engineering modules, leakage validation guards, and experiment artifacts for shipment delay prediction.

---

## Architecture Overview

```text
Processed Dataset (data/processed/shipments_processed.csv)
       │
       ▼
Feature Engineering Pipeline (ml/feature_engineering.py)
 ├── Strict Chronological Ordering (order_date, shipment_id)
 ├── Target Construction (delay_days & delayed)
 ├── Planned Lead Time (expected_delivery_date - order_date)
 ├── Indian Meteorological Season (order_date calendar mapping)
 ├── Transit Route Distance (Logistics hub Haversine + 1.25 circuity)
 ├── Time-Aware Historical Delay (Causal prior-only expanding mean)
 └── Chronological Split (70% Train / 15% Validation / 15% Test)
       │
       ├── Fit Scikit-Learn Preprocessor (on Training Set ONLY)
       ├── Numerical & Categorical Validation (ml/feature_validation.py)
       └── Strict Data Leakage Auditing (ml/leakage_checks.py)
       │
       ▼
Model-Ready Feature Datasets (data/features/)
 ├── regression/ (train.csv, validation.csv, test.csv)
 ├── classification/ (train.csv, validation.csv, test.csv)
 └── metadata/ (feature_schema.json, feature_report.json, split_metadata.json, leakage_report.json, preprocessor.joblib)
```

---

## Approved Model Features (11 Features)

All 11 approved features are strictly available at order creation time:

| Feature | Type | Data Type | Description | Availability Tier |
|---|---|---|---|---|
| `supplier_reliability` | Numerical | `float64` | Known historical supplier score in $[0.0, 1.0]$ | Available at order creation |
| `historical_avg_delay` | Numerical | `float64` | Expanding mean of delays from supplier's prior shipments only (`shift(1)`) | Available at order creation (causal) |
| `lead_time` | Numerical | `int64` | Planned delivery transit days: `(expected - order).days` | Available at order creation |
| `inventory_level` | Numerical | `int64` | On-hand inventory units at origin node | Available at order creation |
| `demand` | Numerical | `int64` | Forecasted SKU order demand at order placement | Available at order creation |
| `quantity` | Numerical | `int64` | Shipment order quantity | Available at order creation |
| `shipping_cost` | Numerical | `float64` | Freight shipping cost quote | Available at order creation |
| `distance` | Numerical | `float64` | Route transit distance in km between logistics hubs | Available at order creation |
| `transport_mode` | Categorical | `object` | Modality: `Road`, `Rail`, `Air`, `Sea` | Available at order creation |
| `season` | Categorical | `object` | Indian season: `Winter`, `Summer`, `Monsoon`, `Post-Monsoon` | Available at order creation |
| `priority` | Categorical | `object` | Dispatch urgency: `Low`, `Medium`, `High`, `Critical` | Available at order creation |

---

## Target Definitions

1. **Regression Target (`delay_days`):**
   $$\text{delay\_days} = \max(0, (\text{actual\_delivery\_date} - \text{expected\_delivery\_date}).\text{days})$$
   Represents non-negative days late (0 indicates on-time or early arrival).

2. **Classification Target (`delayed`):**
   $$\text{delayed} = \begin{cases} 1 & \text{if } \text{delay\_days} > 0 \\ 0 & \text{if } \text{delay\_days} = 0 \end{cases}$$

---

## Data Leakage Prevention Guarantees

The pipeline strictly enforces the following anti-leakage rules:
- **No Realized Delivery Information:** `actual_delivery_date`, realized delay, and realized lead time (`actual_delivery_date - order_date`) are excluded from feature matrices. Using realized lead time would introduce 100% target leakage since $\text{realized\_lead\_time} - \text{planned\_lead\_time} \equiv \text{delay\_days}$.
- **Causal Historical Aggregation:** `historical_avg_delay` is computed via `shift(1).expanding().mean()` grouped by supplier on chronologically sorted records. The current shipment and all future shipments are excluded.
- **Train-Only Preprocessing:** All scalers, imputers, and `OneHotEncoder` pipelines are fit solely on the training split ($70\%$). The validation and test sets are transformed using the fitted preprocessor artifact.
- **No Raw Identifiers as Features:** Arbitrary IDs (`shipment_id`, `supplier_id`, `product_id`) are preserved in `split_audit.csv` for traceability but excluded from predictive feature matrices.

---

## Chronological Split Boundaries

Splits follow a strict chronological ordering:

| Split | Percentage | Row Count | Start Order Date | End Order Date |
|---|---|---|---|---|
| **Train** | 70% | 10,500 | 2023-01-01 | 2025-03-07 |
| **Validation** | 15% | 2,250 | 2025-03-07 | 2025-08-18 |
| **Test** | 15% | 2,250 | 2025-08-18 | 2025-12-31 |

---

## Usage

### Run Feature Engineering Pipeline

To execute the complete end-to-end pipeline:

```bash
python -m ml.feature_engineering
```

Custom input file:

```bash
python -m ml.feature_engineering --input data/processed/shipments_processed.csv
```

### Run Automated Tests

Execute the ML test suite:

```bash
pytest ml/tests -v
```
