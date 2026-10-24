# SupplyPrescript — Operational & Demonstration Runbook

**Phase:** Phase 8 — Production Polish  
**System:** SupplyPrescript Decision Intelligence Platform  
**Target Audience:** Evaluators, Engineers, Solutions Architects, and Operators  

---

## 1. Prerequisites & Environment Setup

### System Requirements:
- **Operating System:** macOS, Linux (Ubuntu 22.04+ recommended), or WSL2 on Windows.
- **Python:** Python 3.10 or 3.11 with pip.
- **Node.js:** Node.js v18.0.0+ and npm v9.0.0+.
- **PostgreSQL:** PostgreSQL 14, 15, or 16 running locally on port 5432.

### Step 1.1: Clone and Configure Environment
```bash
git clone https://github.com/example/supplyprescript.git
cd SupplyPrescript

# Copy configuration template
cp .env.example .env
```

Ensure `.env` matches your local PostgreSQL credentials:
```ini
DATABASE_URL=postgresql+psycopg2://supplyprescript:supplyprescript@localhost:5432/supplyprescript
POSTGRES_DB=supplyprescript
POSTGRES_USER=supplyprescript
POSTGRES_PASSWORD=supplyprescript
BACKEND_URL=http://localhost:8000
FRONTEND_URL=http://localhost:5173
ACTIVE_MODEL_VERSION=v1.0
```

### Step 1.2: Install Dependencies
```bash
# Backend Python dependencies
pip install -r requirements.txt   # or install fastapi uvicorn sqlalchemy psycopg2-binary pulp xgboost scikit-learn pandas pydantic pyjwt passlib bcrypt

# Frontend Node dependencies
cd frontend
npm install
cd ..
```

### Step 1.3: Run Database Migrations
```bash
# Apply all schema revisions up to current head
alembic upgrade head
```

---

## 2. Automated Demonstration (1-Click CLI Runner)

SupplyPrescript includes an automated end-to-end demonstration runner that executes all 12 stages of the operational and learning lifecycle:

```bash
# Run standalone in-process demonstration
PYTHONPATH=backend:optimization python3 scripts/demo_lifecycle.py
```

To run the demonstration against a running FastAPI instance:
```bash
PYTHONPATH=backend:optimization python3 scripts/demo_lifecycle.py --api-url http://localhost:8000
```

### What the Script Verifies:
1. **RBAC Token Issuance:** Authenticates `operator` and `admin`.
2. **Operational Ingestion:** Submits a critical shipment to `POST /api/shipments`.
3. **ML Prediction:** Uses real XGBoost model `v1.0` to infer delay probability & days.
4. **Prescriptive Optimization:** Generates 3 alternatives via PuLP MILP solver.
5. **Safety Gate Audit:** Verifies inventory safety stock compliance.
6. **Decision Write-Back:** Executes the Air Freight recommendation with an idempotency key.
7. **Idempotency Safeguard:** Proves identical replay returns 200 OK and tampered payload returns 409 Conflict.
8. **Outcome Recording:** Ingests physical delivery actuals into `POST /api/decisions/{id}/outcome`.
9. **Decision ROI Engine:** Calculates cost/delay variance, money saved, and net ROI.
10. **Feedback Dataset Snapshot:** Ingests outcome into verified model feedback observations.
11. **Continuous Retraining:** Queries drift telemetry and validates candidate retraining.
12. **Promotion & Safe Rollback:** Blocks unauthorized operator promotion and rolls back to `v1.0`.
13. **Clean Teardown:** Purges demo records from PostgreSQL, leaving total count exactly intact.

---

## 3. Running the Interactive Full-Stack Application

### Step 3.1: Start Backend API Server
```bash
# In Terminal 1:
PYTHONPATH=backend:optimization uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger / OpenAPI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### Step 3.2: Start Frontend Development Server
```bash
# In Terminal 2:
cd frontend
npm run dev
```
- Application Web UI: [http://localhost:5173](http://localhost:5173)

---

## 4. Interactive Web UI Demonstration Flow

### Role Credentials:
| Role | Username | Password | Permissions |
| :--- | :--- | :--- | :--- |
| **Operator** | `operator` | `Operator123!` | Operational intake, prediction, decision execution, outcome recording. |
| **Analyst** | `analyst` | `Analyst123!` | Read analytics, ROI dashboard, generate feedback datasets. |
| **Admin** | `admin` | `Admin123!` | Retraining execution, candidate promotion, emergency rollback. |

### Walkthrough Steps in Browser:
1. **Navigate to Command Center (`/command-center`):**
   - Inspect active high-risk shipments.
   - Enter a shipment parameter profile or select an existing shipment.
   - Click **Run ML Prediction & Optimization**.
   - Review the dual XGBoost delay probability, risk score, and the 3 generated alternatives.
   - Inspect the **Safety Gate Compliance** indicator on each alternative card.
   - Click **Execute Recommendation** on the Air Freight Expedited card.
   - Confirm execution in the modal.
2. **Review Decision History (`/history`):**
   - Verify the newly recorded decision appears with status `EXECUTED` and unique `DEC-EXEC-...` ID.
   - Inspect the captured model version, timestamp, and audit metadata.
3. **Record Operational Delivery Outcome (`/outcomes`):**
   - Locate the executed decision.
   - Click **Record Actual Outcome**.
   - Input delivery date, actual landed cost, and carrier notes.
   - Submit and review the real-time **Predicted vs Actual Variance** card.
4. **Analyze Financial Impact in Decision ROI Dashboard (`/roi-dashboard`):**
   - Inspect portfolio-level KPIs: Success Rate %, Net Money Saved ($), Average Cost Variance.
   - Review the **Decision Success Breakdown** chart and **Strategy ROI Comparison** table.
5. **Inspect Feedback & Continuous Learning (`/retraining`):**
   - Check the **Active Model Health** card.
   - Review the **Feedback Dataset Snapshot** table showing paired predictions and outcomes.
   - Review performance degradation telemetry.
   - As `admin`, click **Run Retraining Check**.
   - Review candidate validation score vs baseline.
   - Test **Emergency Rollback** to instantly reinstate `v1.0`.

---

## 5. Automated Test Suite Execution

### Backend Pytest Suite (303 Tests)
```bash
PYTHONPATH=backend:optimization pytest tests/ -v
```
Expected output:
```text
======================= 303 passed, 39 warnings in ~13.5s =======================
```

### Frontend Vitest Suite (64 Tests)
```bash
cd frontend
npm test -- --run
```
Expected output:
```text
Test Files  17 passed (17)
     Tests  64 passed (64)
```

### Frontend Production Build Verification
```bash
cd frontend
npm run build
```
Expected output:
```text
vite v5.4.14 building for production...
✓ 164 modules transformed.
dist/index.html                   0.85 kB │ gzip:  0.43 kB
dist/assets/index-B_VwHh6O.css   18.12 kB │ gzip:  3.94 kB
dist/assets/index-CknB-yE7.js   346.85 kB │ gzip: 98.42 kB
✓ built in ~1.5s
```

---

## 6. Troubleshooting & Reset

### Problem: Tests fail with `assert 15001 == 15000`
**Cause:** Stray demo records created during interrupted manual testing.  
**Resolution:** Clean stray demo records using the automated cleanup command:
```bash
PYTHONPATH=backend python3 -c "
from app.database.connection import SessionLocal
from app.models.shipment import Shipment
from app.models.decision import Decision
from app.models.outcome import Outcome
from app.models.feedback import Feedback

db = SessionLocal()
for s in db.query(Shipment).filter(Shipment.shipment_id.like('SHIP-DEMO%')).all():
    decs = db.query(Decision).filter(Decision.shipment_id == s.shipment_id).all()
    for d in decs:
        db.query(Outcome).filter((Outcome.decision_id == d.id) | (Outcome.decision_business_id == d.decision_id)).delete(synchronize_session=False)
        db.query(Feedback).filter((Feedback.decision_id == d.decision_id) | (Feedback.shipment_id == s.shipment_id)).delete(synchronize_session=False)
        db.delete(d)
    db.delete(s)
db.commit()
print('Total shipments in DB:', db.query(Shipment).count())
db.close()
"
```
