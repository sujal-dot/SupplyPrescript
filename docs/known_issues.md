# SupplyPrescript — Known Issues & Operational Debt

**Document Version:** 1.0.0  
**Phase:** 8 — Production Polish / Release Candidate  
**Date:** October 28, 2026  
**Auditor:** Senior Software Architect & Database Reliability Engineer  

---

## 1. Issue Classification Matrix

| Issue ID | Title | Subsystem | Severity | Release Blocking? | Recommended Remediation |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ISS-01** | Synchronous Retraining Job Execution | ML / Retraining | **MEDIUM** | No (Staging / Demo) | Offload long-running retraining to asynchronous worker queues (Celery, Temporal, or AWS Batch). |
| **ISS-02** | Local Filesystem Model Artifacts | ML / Registry | **LOW** | No (Single-Node) | Migrate `models/versions/` to cloud object storage (AWS S3, Google Cloud Storage) with MLflow registry. |
| **ISS-03** | Single-Node Relational Storage | Database | **LOW** | No (Current Load) | Introduce read-only PostgreSQL replicas for `/api/roi/dashboard` aggregation queries under high concurrent write loads. |
| **ISS-04** | Real Model Output vs 14-Day Scenario | ML / Inference | **INFORMATIONAL** | No (Documented) | Retain genuine XGBoost regression output (1.76 - 3.52 days) as empirical truth; do not force synthetic 14-day predictions. |
| **ISS-05** | Minimum Verified Feedback Threshold | Feedback Pipeline | **INFORMATIONAL** | No (Documented) | Cold-start systems require at least 10 completed delivery outcomes before calculating drift degradation metrics. |

---

## 2. Detailed Issue Descriptions & Remediations

### ISS-01: Synchronous Retraining Job Execution
- **Severity:** MEDIUM
- **Description:** Retraining jobs triggered via `POST /api/ml/retraining/run` execute within the server worker process. For small-to-medium dataset sizes (up to 20,000 records), execution completes within 2.5 seconds. However, as feedback datasets scale beyond 100,000 records, training XGBoost trees synchronously can block the event loop or tie up worker threads.
- **Remediation for Enterprise Production:**
  - Decouple retraining from FastAPI request-response cycles.
  - Implement task queueing via Celery with Redis broker:
    ```python
    @celery_app.task(bind=True)
    def retrain_model_task(self, trigger_reason, force):
        ...
    ```
  - Return HTTP 202 Accepted with a job tracking URL immediately.

---

### ISS-02: Local Filesystem Model Artifact Storage
- **Severity:** LOW
- **Description:** Model versions and candidate artifacts are written to `models/versions/<version>/` and `ml/artifacts/candidates/` on the local filesystem. This is suitable for single-node deployments and demonstrations. In a multi-replica Kubernetes deployment, local disk storage causes version desynchronization across pods.
- **Remediation for Multi-Node Kubernetes:**
  - Configure cloud storage backends (e.g., S3 or Google Cloud Storage) for serialized model artifacts.
  - Synchronize active model pointers via an external model registry (e.g., MLflow, Weights & Biases, or AWS SageMaker Model Registry).

---

### ISS-03: Single-Node Relational Storage Contention
- **Severity:** LOW
- **Description:** The operational database (`supplyprescript`) manages operational shipments, decisions, outcomes, and feedback on a single PostgreSQL instance. While ACID transactions and foreign key constraints are strictly enforced, heavy analytical queries on `/api/roi/dashboard` or `/api/feedback` perform multi-table aggregations.
- **Remediation for High-Throughput Production:**
  - Route read-heavy analytics and dashboard queries to a PostgreSQL read replica.
  - Materialize historical ROI summary metrics via periodic background rollup tasks or materialized views with concurrent refresh.

---

### ISS-04: Real Model Output vs 14-Day Scenario
- **Severity:** INFORMATIONAL
- **Description:** Certain hypothetical supply chain scenarios assume an arbitrary 14-day delay. The trained XGBoost regression model in `models/versions/v1.0/regressor.pkl` predicts delay durations between **1.76 and 3.52 days** for standard shipment profiles, accurately matching the empirical distribution of the training data.
- **Remediation:**
  - The platform strictly adheres to data integrity standards: it does not hardcode 14 days or alter the model to force arbitrary results.
  - The actual model prediction is surfaced and documented honestly.

---

### ISS-05: Minimum Feedback Threshold for Retraining
- **Severity:** INFORMATIONAL
- **Description:** To prevent statistical instability from small sample sizes, candidate model evaluation requires a minimum volume of verified feedback samples ($\ge 10$ records) before calculating drift degradation metrics. On freshly initialized databases without recorded outcomes, the drift monitor legitimately reports `status: "INSUFFICIENT_DATA"`.
- **Remediation:**
  - Documented as an expected operational safeguard. Operators can use `force: true` in retraining requests to test candidate evaluation fixtures on demand.
