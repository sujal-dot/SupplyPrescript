# SupplyPrescript — Versioned Model Feedback Datasets

**Phase:** 7 — Continuous Learning  
**Date:** October 25, 2026  

---

## 1. Directory Structure

```text
data/feedback/
├── README.md               # This documentation
├── manifests/              # Versioned JSON manifests detailing dataset metadata & checksums
└── exports/                # Exported CSV snapshots of eligible feedback observations
```

---

## 2. Dataset Requirements & Governance

1. **Source of Truth:**
   The PostgreSQL `model_feedbacks` table serves as the authoritative operational source of truth. Snapshots stored here provide immutable, reproducible point-in-time training and evaluation datasets.

2. **Deduplication & Lineage:**
   Each record links directly back to its original `prediction_id`, `shipment_id`, and `decision_id`. Repeated feedback generation runs update existing observations rather than duplicating them.

3. **Prediction Error Sign Convention:**
   $$\text{prediction\_error} = \text{actual\_delay} - \text{predicted\_delay}$$
   $$\text{absolute\_error} = |\text{actual\_delay} - \text{predicted\_delay}|$$
   - **Positive error:** Actual delivery delay exceeded predicted delay (arrived later than forecast).
   - **Negative error:** Actual delivery delay was lower than predicted delay (arrived earlier than forecast).
   - **Zero error:** Exact delivery milestone match.

4. **Eligibility Criteria:**
   - Prediction exists and is linked to a valid shipment.
   - Model version was recorded at prediction time (never retrofitted or assumed from active model).
   - Operational outcome is finalized (`outcome_status` is `DELIVERED` or `Success`, not `AWAITING_DELIVERY` or `DISPUTED`).
   - Actual delay is a valid non-negative number ($\ge 0$).

5. **No Automatic Retraining or Promotion:**
   This pipeline evaluates model performance over time. Production models are never automatically replaced or promoted without human engineering review.
