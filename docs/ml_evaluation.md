# SupplyPrescript — ML Evaluation and Model Versioning Guide

## Overview

This document defines the evaluation standards, metrics definitions, model versioning lifecycle, and operational procedures for the **SupplyPrescript** predictive machine learning engine.

The engine powers shipment delay intelligence using two coordinated XGBoost models:
1. **Shipment Delay Classifier (`XGBClassifier`):** Predicts the binary risk that a shipment will arrive late (`delayed` $\in \{0, 1\}$).
2. **Shipment Delay Regressor (`XGBRegressor`):** Predicts the continuous number of delay days (`delay_days` $\ge 0$).

---

## 1. Evaluation Methodology

### Chronological Test Set Segregation
All final evaluation metrics are computed strictly on the untouched **chronological test split**:
- **Dataset Source:** `data/features/classification/test.csv` & `data/features/regression/test.csv`
- **Total Test Records:** 2,250 shipments (15% of the 15,000 historical shipment dataset)
- **Time Separation:** The test records occur chronologically after the 10,500 training records and 2,250 validation records.
- **Zero-Leakage Assurance:** The test set was never used to fit the `ColumnTransformer`, imputers, or scalers, nor used for hyperparameter optimization. The decision threshold (`0.150`) was tuned exclusively on the validation split.

---

## 2. Evaluation Metrics Definitions

### Binary Classification Metrics

1. **Accuracy**
   $$\text{Accuracy} = \frac{TP + TN}{TP + TN + FP + FN}$$
   - *Definition:* Fraction of total shipments correctly classified as on-time or delayed.
   - *Context:* On imbalanced data (23.2% delayed), raw accuracy can be misleading if evaluated alone; it is reported alongside recall and precision.

2. **Precision**
   $$\text{Precision} = \frac{TP}{TP + FP}$$
   - *Definition:* The proportion of shipments predicted as delayed that actually arrived late.
   - *Zero-Division Safety:* If the model predicts zero delayed shipments, precision is documented as `0.0` safely via `zero_division=0`.

3. **Recall (Sensitivity)**
   $$\text{Recall} = \frac{TP}{TP + FN}$$
   - *Definition:* The proportion of actual delayed shipments successfully flagged by the model.
   - *Business Importance:* Critical for supply chain logistics. Missing a delayed shipment (False Negative) causes assembly line shutdowns and stockouts.

4. **F1-Score**
   $$\text{F1} = 2 \cdot \frac{\text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$
   - *Definition:* Harmonic mean of precision and recall.

5. **ROC-AUC (Receiver Operating Characteristic — Area Under Curve)**
   - *Definition:* Measures the ranking discriminative capability of continuous probability scores across all potential decision thresholds.
   - *Computation:* Evaluated strictly using `predict_proba()[:, 1]`.
   - *Edge Case Handling:* If the test data has only one class, ROC-AUC is recorded as `None` with an explicit reason string.

6. **Brier Score Loss**
   $$\text{Brier} = \frac{1}{N} \sum_{i=1}^N (p_i - y_i)^2$$
   - *Definition:* Mean squared difference between predicted probability and actual binary outcome; measures probability calibration.

---

### Continuous Regression Metrics

1. **MAE (Mean Absolute Error)**
   $$\text{MAE} = \frac{1}{N} \sum_{i=1}^N |y_i - \hat{y}_i|$$
   - *Definition:* Average magnitude of prediction errors in days.
   - *Interpretation:* Lower is better. Robust against extreme outlier penalties.

2. **RMSE (Root Mean Squared Error)**
   $$\text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^N (y_i - \hat{y}_i)^2}$$
   - *Definition:* Square root of mean squared error. Heavily penalizes large delay prediction discrepancies.

3. **R² (Coefficient of Determination)**
   $$R^2 = 1 - \frac{\sum_{i=1}^N (y_i - \hat{y}_i)^2}{\sum_{i=1}^N (y_i - \bar{y})^2}$$
   - *Definition:* Proportion of target variance explained by the model relative to a mean baseline.
   - *Edge Case Handling:* Safely handles constant targets or single-sample test sets by setting $R^2$ to `None` with a logged reason.
   - *Domain Context:* For zero-inflated delay distributions (where ~77% of shipments have exactly 0 days delay), $R^2$ can be negative if the model predicts small non-zero delays across the zero mass.

4. **Median Absolute Error (MedAE)**
   $$\text{MedAE} = \text{median}(|y_1 - \hat{y}_1|, \dots, |y_N - \hat{y}_N|)$$
   - *Definition:* Median magnitude of delay errors; insensitive to heavy tail outliers.

---

## 3. Production Test Evaluation Results (Release v1.0)

Evaluated on **2,250 untouched test shipments**:

| Metric | Classification Model (`XGBClassifier`) | Metric | Regression Model (`XGBRegressor`) |
| :--- | :--- | :--- | :--- |
| **Accuracy** | 32.58% | **MAE** | 2.0369 days |
| **Precision** | 24.09% | **Median AE** | 1.7822 days |
| **Recall** | **88.34%** | **RMSE** | 2.9089 days |
| **F1-Score** | 37.85% | **Max Error** | 22.7797 days |
| **ROC-AUC** | **0.5822** | **Mean Actual** | 1.0151 days |
| **PR-AUC** | 0.2960 | **Target Min/Max** | 0.00 / 27.00 days |
| **Threshold** | 0.150 (Tuned for Recall) | **Samples** | 2,250 rows |
| **Delayed Ratio** | 23.24% (523 Delayed / 1,727 On-Time) | **Constraint** | Non-negative ($\ge 0$ days) |

---

## 4. Model Versioning Architecture & Policy

### Directory Layout

```text
SupplyPrescript/
├── models/
│   ├── xgboost_delay_model.pkl       # Primary documented compatibility artifact
│   └── versions/
│       ├── active.json               # Atomic pointer to production active version
│       └── v1.0/                     # Release v1.0 package
│           ├── classifier.pkl        # Serialized XGBClassifier
│           ├── regressor.pkl         # Serialized XGBRegressor
│           ├── preprocessor.pkl      # Fitted ColumnTransformer
│           ├── metadata.json         # Checksums, parameters, schemas, lineage
│           └── metrics.json          # Complete evaluation scores
```

### Primary Compatibility Artifact
`models/xgboost_delay_model.pkl`:
- **Purpose:** Serves as the primary single-file delay model artifact.
- **Contents:** Exact copy of the active production `XGBClassifier` model.
- **Parity Guarantee:** Verified to produce byte-for-byte identical predictions to `models/versions/v1.0/classifier.pkl`.

### Versioning Rules & Semantic Policy
1. **Initial Release:** `v1.0` represents the initial approved baseline release.
2. **Minor Versioning (`v1.1`, `v1.2`):**
   - Retrained models on expanded historical data.
   - Hyperparameter optimizations without altering the 11-feature contract.
3. **Major Versioning (`v2.0`):**
   - Schema modifications (e.g. adding weather API features or port congestion metrics).
   - Changes to the inference API response contract.
4. **Immutability & Safety:**
   - Existing versions cannot be overwritten silently without explicit flags (`overwrite=True`).
   - Promotions are atomic (via temporary files and `os.replace`).
   - If artifact verification or smoke testing fails, the promotion is aborted and the previous active model is preserved.

---

## 5. CLI Execution Commands

### Run Model Evaluation
```bash
# Evaluate both classification and regression models on the test set
python -m ml.evaluate

# Evaluate classification only
python -m ml.evaluate --task classification

# Evaluate regression only
python -m ml.evaluate --task regression

# Evaluate and register/promote as a new version
python -m ml.evaluate --register-version v1.0
```

### Manage Model Registry & Versioning
```bash
# List all registered versions and their active status
python -m ml.model_registry --list

# Show currently active production version
python -m ml.model_registry --active

# Verify artifacts, SHA-256 checksums, and smoke-test prediction
python -m ml.model_registry --verify v1.0

# Safely promote a candidate version to active production
python -m ml.model_registry --promote v1.0
```

### Run Automated Tests
```bash
# Run Day 8 evaluation and versioning tests
pytest tests/ml/test_evaluate.py tests/ml/test_model_registry.py tests/ml/test_model_versioning.py tests/ml/test_model_loading.py -v

# Run the complete test suite across the repository
pytest -v
```

---

## 6. Real-Time Inference Integration

Inference calls automatically load the active registered version:

```python
from ml.predict import predict_shipment

sample_shipment = {
    "supplier_reliability": 0.85,
    "historical_avg_delay": 1.2,
    "lead_time": 7,
    "inventory_level": 350,
    "demand": 400,
    "quantity": 150,
    "shipping_cost": 120.0,
    "distance": 450.0,
    "transport_mode": "Road",
    "season": "Monsoon",
    "priority": "High",
}

prediction = predict_shipment(sample_shipment)
print(prediction)
```

**Output:**
```json
{
  "delayed": true,
  "delay_probability": 0.4054,
  "predicted_delay_days": 0.77,
  "classification_threshold": 0.150,
  "model_version": "v1.0",
  "disagreement_warning": null,
  "prediction_timestamp": "2026-10-11T05:46:33.988522+00:00"
}
```

---

## 7. Known Limitations & Recommendations

1. **Class Imbalance:**
   - 23.2% of test shipments are delayed. The optimal threshold `0.150` achieves high operational recall (**88.34%**), ensuring that potential delays are flagged early, but trades off precision (24.09%).
2. **Regression Zero-Inflation:**
   - Most shipments experience 0 days delay. For production, combining classification gating with regression conditional on delay is recommended for Day 9+.
3. **Artifact Security:**
   - Checksums prevent tampering; model artifacts should only be written and loaded from trusted local paths.
