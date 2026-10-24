# SupplyPrescript — Operational Runbook & Deployment Guide (Day 24)

**Document Version:** 1.0.0  
**Phase:** 8 — Production Polish  
**Date:** October 27, 2026  
**Audience:** Site Reliability Engineers, DevOps Engineers, System Administrators, ML Platform Engineers  

---

## 1. System Architecture & Prerequisites

SupplyPrescript consists of:
- **Frontend:** React 18 SPA built with Vite, Tailwind CSS, Lucide icons, and Recharts.
- **Backend API:** FastAPI (Python 3.10+) with SQLAlchemy 2.0 ORM and Pydantic v2 schemas.
- **Database:** PostgreSQL 15+ with relational schema and Alembic migrations.
- **Prescriptive Optimization Engine:** PuLP LP/MIP solver enforcing Day 15 hard constraints.
- **Machine Learning Engine:** Scikit-Learn pipelines & XGBoost regressor/classifier models.

### Prerequisites

| Component | Minimum Version | Recommended |
|---|---|---|
| Python | 3.10+ | 3.10.13 |
| Node.js | 18+ | 20 LTS |
| PostgreSQL | 14+ | 15 / 16 |
| Memory | 4 GB | 8 GB+ |
| Disk | 10 GB | 20 GB SSD |

---

## 2. Environment Configuration

Copy the sanitized template to create your staging or production environment file:

```bash
cp .env.example .env
```

Ensure the following variables are customized:

```bash
APP_ENV=production
APP_DEBUG=false
AUTH_REQUIRED=true
AUTH_SECRET_KEY=<generate_secure_random_64_char_string>
DATABASE_URL=postgresql+psycopg2://user:password@db-host:5432/supplyprescript
CORS_ORIGINS=["https://app.supplyprescript.internal"]
```

---

## 3. Database Migrations & Initial Seeding

Apply database schema migrations to the latest revision (`b825c719e0f2`):

```bash
# Run migrations to head
alembic upgrade head
```

Verify migration status:

```bash
alembic current
# Expected output: b825c719e0f2 (head)
```

The system automatically initializes default user accounts with secure bcrypt passwords if the user table is empty.

---

## 4. Starting the Services

### A. Backend FastAPI Service

```bash
# In production with Uvicorn workers
uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8000 --workers 4 --proxy-headers
```

### B. Frontend Service

```bash
# Build production bundle
cd frontend
npm ci
npm run build

# Serve statically (e.g. Nginx, Caddy, or static host)
# Development preview:
npm run preview -- --host 0.0.0.0 --port 5173
```

---

## 5. Health Checks & Monitoring

The application exposes structured health check endpoints:

1. **Service Liveness:**
   ```bash
   curl -s http://localhost:8000/health
   # Response: {"status": "healthy", "service": "supplyprescript-api"}
   ```

2. **Database Connectivity:**
   ```bash
   curl -s http://localhost:8000/health/db
   # Response: {"status": "connected", "database": "postgresql"}
   ```

3. **Model Retraining & Drift Monitor:**
   ```bash
   curl -s -H "Authorization: Bearer <ADMIN_TOKEN>" http://localhost:8000/api/ml/retraining/monitor
   # Response: {"is_degraded": false, "status": "HEALTHY", ...}
   ```

---

## 6. Model Retraining, Promotion & Rollback Runbook

### A. Evaluating Model Performance

Administrators can evaluate active production model performance against verified feedback:

```bash
curl -X POST http://localhost:8000/api/feedback/evaluate \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"model_version": "v1.0", "min_sample_threshold": 10}'
```

### B. Triggering Monitored Retraining

```bash
curl -X POST http://localhost:8000/api/ml/retraining/run \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

### C. Promoting an Approved Candidate

When candidate validation passes and status is `REGISTERED`:

```bash
curl -X POST http://localhost:8000/api/ml/retraining/jobs/<JOB_ID>/promote \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

### D. Emergency Model Rollback

If performance degradation or unexpected prediction behavior is observed in production, roll back immediately:

```bash
curl -X POST http://localhost:8000/api/ml/retraining/rollback \
  -H "Authorization: Bearer <ADMIN_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"target_version": "v1.0"}'
```

The rollback engine automatically:
1. Validates that `v1.0` artifacts exist on disk.
2. Updates `models/versions/active.json`.
3. Updates `model_versions` table in PostgreSQL.
4. Reloads active models into memory.
5. Returns `{"status": "SUCCESS", "active_version": "v1.0"}`.
