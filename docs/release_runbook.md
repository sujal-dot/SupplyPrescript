# SupplyPrescript — Production Release Runbook

**Document Version:** 1.0.0  
**Target Release:** Release Candidate 1 (v1.0.0-rc1)  
**Date:** October 28, 2026  
**Audience:** Site Reliability Engineers, DevOps Leads, and Release Engineers  

---

## 1. Pre-Deployment Release Checklist

Before initiating deployment to staging or production environments, verify the following gates:

- [ ] **Git Working Tree:** Clean git status on `main` branch with no uncommitted debug changes.
- [ ] **Backend Tests:** All 303 pytest tests pass (`PYTHONPATH=backend:optimization pytest tests/ -q`).
- [ ] **Optimization Tests:** All 137 optimization tests pass (`PYTHONPATH=backend:optimization pytest optimization/tests/ -q`).
- [ ] **Frontend Tests:** All 64 Vitest tests pass (`cd frontend && npm test -- --run`).
- [ ] **Frontend Production Build:** Clean build artifacts generated in `frontend/dist/` (`npm run build`).
- [ ] **Active Model Artifacts:** `models/versions/v1.0/` contains verified `classifier.pkl`, `regressor.pkl`, and `preprocessor.pkl`.
- [ ] **Database Backup:** Full PostgreSQL dump executed and stored in secure backup location:
  ```bash
  pg_dump -U supplyprescript -d supplyprescript -Fc -f supplyprescript_pre_v1.0.dump
  ```

---

## 2. Environment Configuration

Verify target environment variables in `/etc/supplyprescript/.env` or container environment:

```ini
# Core Configuration
APP_ENV=production
APP_DEBUG=false
LOG_LEVEL=INFO

# Operational Database
DATABASE_URL=postgresql+psycopg2://<db_user>:<db_pass>@<db_host>:5432/supplyprescript
POSTGRES_DB=supplyprescript

# Service Networking & CORS
BACKEND_URL=https://api.supplyprescript.internal
FRONTEND_URL=https://app.supplyprescript.internal
CORS_ORIGINS=["https://app.supplyprescript.internal"]

# Authentication & Hardening
AUTH_ENABLED=true
AUTH_REQUIRED=true
AUTH_SECRET_KEY=<generate_cryptographically_secure_random_key_64_chars>
AUTH_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# ML Inference & Active Model Registry
ACTIVE_MODEL_VERSION=v1.0
RISK_THRESHOLD_LOW=0.30
RISK_THRESHOLD_HIGH=0.70

# Continuous Retraining Safeguards
RETRAINING_MIN_FEEDBACK_THRESHOLD=10
RETRAINING_MIN_TRAIN_SAMPLES=50
RETRAINING_MIN_VAL_SAMPLES=15
RETRAINING_DEGRADATION_MAE_THRESHOLD_PCT=15.0
RETRAINING_DEGRADATION_MAE_ABSOLUTE_DAYS=0.25
RETRAINING_MIN_IMPROVEMENT_PCT=3.0
RETRAINING_MAX_SECONDARY_REGRESSION_PCT=10.0
RETRAINING_COOLDOWN_MINUTES=60
RETRAINING_MAX_CONCURRENT_JOBS=1
RETRAINING_AUTO_PROMOTION_ENABLED=false
RETRAINING_CANDIDATES_DIR=ml/artifacts/candidates
```

---

## 3. Database Migration Deployment

Execute database schema migrations to the latest Alembic revision:

```bash
# Check current revision
alembic current

# Apply migrations up to head revision
alembic upgrade head

# Verify target revision
alembic current
# Expected: b825c719e0f2 (head)
```

---

## 4. Backend Service Startup & Verification

### 4.1 Systemd Service Unit or Container Launch
```bash
# Example Systemd unit startup
sudo systemctl restart supplyprescript-backend

# Or via Docker / Uvicorn production worker
PYTHONPATH=backend:optimization uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --timeout-keep-alive 30 \
  --access-log
```

### 4.2 Liveness & Readiness Verification
```bash
# 1. Verify HTTP Liveness
curl -fsSL http://localhost:8000/health
# Response: {"status": "healthy"}

# 2. Verify Database Readiness
curl -fsSL http://localhost:8000/health/db
# Response: {"status": "healthy", "database": "connected"}
```

---

## 5. Frontend SPA Deployment

### 5.1 Build Static Assets
```bash
cd frontend
npm ci --production=false
npm run build
```

### 5.2 Deploy to Nginx / CDN
Deploy `frontend/dist/` contents to web root (e.g., `/var/www/supplyprescript/html`).

Example Nginx Configuration:
```nginx
server {
    listen 80;
    server_name app.supplyprescript.internal;

    root /var/www/supplyprescript/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $http_x_request_id;
    }
}
```

---

## 6. Post-Deployment Smoke Test Protocol

Execute the automated lifecycle smoke test against the live running deployment:

```bash
# Run automated 12-stage validation runner
PYTHONPATH=backend:optimization python3 scripts/demo_lifecycle.py --api-url http://localhost:8000
```

Verify that all 12 stages pass:
1. Operator & Admin authentication.
2. Shipment registration.
3. ML inference (`v1.0`).
4. Optimization & Safety Gate evaluation.
5. Decision write-back & idempotency.
6. Actual outcome ingestion.
7. Decision ROI calculation.
8. Feedback observation generation.
9. Retraining monitor query.
10. Promotion safeguard check (403 for operator).
11. Emergency rollback to `v1.0`.
12. Database record teardown (15,000 count preserved).

---

## 7. Emergency Rollback Procedures

### 7.1 Instant Model Rollback
If a newly promoted model displays abnormal prediction behavior in production, revert immediately to stable `v1.0`:

```bash
# Via REST API (requires Admin token)
curl -X POST http://localhost:8000/api/ml/retraining/rollback \
  -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"target_version": "v1.0"}'

# Or via Python CLI
python3 -m ml.model_registry --promote v1.0
```

### 7.2 Database Schema Rollback
If a schema migration introduces an unexpected defect:

```bash
# Downgrade one revision
alembic downgrade -1

# Or restore pre-deployment database dump
pg_restore -U supplyprescript -d supplyprescript --clean supplyprescript_pre_v1.0.dump
```

### 7.3 Frontend SPA Rollback
Revert web server symlink to the previous static build directory:
```bash
sudo ln -sfn /var/www/supplyprescript/releases/v0.9.9 /var/www/supplyprescript/html
sudo systemctl reload nginx
```
