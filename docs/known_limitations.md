# SupplyPrescript — Known Limitations & Architectural Boundaries

**Phase:** Phase 8 — Production Polish  
**Version:** 1.0.0  
**Scope:** Technical constraints, operational assumptions, and production scaling prerequisites.

---

## 1. Machine Learning & Predictive Limitations

### 1.1 Delay Prediction Distribution vs Edge Cases
- **Empirical Training Range:** The trained XGBoost regression model in `models/versions/v1.0/regressor.pkl` predicts delay durations typically ranging from **1.5 to 4.0 days** for standard shipment profiles. This reflects the historical empirical distribution of the training dataset.
- **Extreme Disruption Boundaries:** The models predict incremental operational delays based on supplier reliability, lead times, priority, and transit modes. They do not model unprecedented black swan events (e.g., global canal blockages, war-related air corridor closures) without external feature engineering.
- **Prediction Label Lineage:** Continuous retraining uses verified actual operational delivery delay ($\text{actual\_delay}$) as the ground truth label. It does not train on the error delta field ($\text{prediction\_error}$), ensuring valid regression target definitions.

---

## 2. Optimization Solver & Prescriptive Limitations

### 2.1 Solver Scalability & Solvability
- **Solver Engine:** Uses the open-source CBC solver wrapped by PuLP.
- **Scope of Formulation:** The prescriptive engine formulates 3 distinct discrete operational alternatives (Air Freight, Secondary Supplier, Accept Delay) per critical shipment. Solve time is $< 300\text{ ms}$ per shipment.
- **Enterprise Network Scale:** The current solver optimizes decisions on an individual shipment or batch level. It does not solve multi-echelon network-wide supply chain flows with millions of simultaneous integer constraints across global warehouse nodes. For global multi-echelon inventory optimization (MEIO), integration with enterprise solvers (e.g., Gurobi, CPLEX) or distributed decomposition algorithms would be required.

---

## 3. Data Ingestion & Continuous Feedback Boundaries

### 3.1 Feedback Eligibility Rules
- A decision write-back record is not equivalent to a completed delivery.
- The feedback pipeline strictly validates eligibility before adding records to continuous learning datasets:
  - Shipments with status `PENDING`, `IN_TRANSIT`, or `CANCELLED` are marked as `PENDING_OUTCOME` or `EXCLUDED`.
  - Only records with verified `actual_cost`, `actual_delivery_date`, and verified `actual_delay` qualify as `ELIGIBLE`.

### 3.2 Feedback Volume Thresholds
- To prevent statistical instability from small sample sizes, candidate model evaluation requires a minimum volume of verified feedback samples ($\ge 10$ records) before calculating drift degradation metrics.

---

## 4. Concurrency, Infrastructure & Deployment Prerequisites

### 4.1 Retraining Execution Architecture
- **Current State:** Retraining jobs are executed within the application process or background tasks, writing serialized artifacts to `ml/artifacts/candidates/` and `models/versions/`.
- **Production Prerequisite:** For high-traffic enterprise staging, retraining should be decoupled from the FastAPI web worker process and executed via an asynchronous task orchestrator (e.g., Celery, Temporal, or AWS Batch) with MLflow model registry integration.

### 4.2 Storage & File Locking
- Model versioning metadata is stored in `config/model_registry.json`. File-level concurrency locking is implemented for rollbacks and promotions, but a distributed key-value store (e.g., Redis, etcd) or relational database registry is recommended for multi-node Kubernetes clusters.

### 4.3 Database Read/Write Segregation
- The operational database (`supplyprescript`) manages operational shipments, decisions, outcomes, and feedback on a single PostgreSQL instance. For enterprise production throughput exceeding 10,000 write operations/second, read-heavy analytics (`/api/roi/dashboard`) should be directed to read-only database replicas.

---

## 5. Security & Authentication Boundaries

### 5.1 Local Credential Defaults
- Default seeded accounts (`operator`, `analyst`, `admin`) use deterministic test passwords (`Operator123!`, etc.) for local demonstration convenience.
- In staging/production environments, `AUTH_REQUIRED=true` must be set in `.env`, and secret keys (`AUTH_SECRET_KEY`) must be injected via secure secret managers (e.g., AWS Secrets Manager, HashiCorp Vault).
