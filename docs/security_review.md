# SupplyPrescript — Application Security Review & Hardening Audit

**Document Version:** 1.0.0  
**Phase:** 8 — Production Polish / Release Candidate  
**Date:** October 28, 2026  
**Auditor Roles:** Senior Application Security Engineer, Full-Stack Engineer, ML Platform Engineer  

---

## 1. Threat Model & Security Posture

SupplyPrescript coordinates mission-critical supply chain decision making, automated alternative prescription, and continuous machine learning model retraining. Compromising decision write-backs or model registry versions poses financial, operational, and physical supply chain risks.

### Identified Threat Vectors & Implemented Mitigations

| Threat Vector | Potential Impact | Severity | Implemented Mitigation | Verification Mechanism |
|---|---|---|---|---|
| **Identity Spoofing** | Attacker transmits arbitrary `user_id` in request payloads to impersonate executives or operations managers. | **Critical** | Server-side principal derivation in `get_current_user`. The acting `user_id` and `approved_by` are strictly extracted from signed JWT claims. Client payload identity fields are ignored. | Verified in `tests/security/test_security_and_hardening.py::test_identity_spoofing_prevented_principal_enforced`. |
| **Privilege Escalation** | An operator or analyst triggers automatic retraining, candidate promotion, or production rollback. | **High** | Role-Based Access Control (RBAC) enforced via FastAPI dependencies (`require_roles` / `require_permission`). Only accounts with `Role.ADMIN` can execute retraining, promotion, or rollback. | Verified in `tests/security/test_security_and_hardening.py` across operator and analyst restriction tests. |
| **Client Value Tampering** | Manipulated predicted cost, delay probability, or fake feasibility flags sent by frontend client. | **Critical** | Authoritative server-side recalculation in `POST /api/decisions`. The server resolves shipment data directly from PostgreSQL, runs alternative generation, and re-evaluates all PuLP constraints independently. | Verified in `tests/api/test_decisions.py` and `tests/e2e/test_full_system_lifecycle.py`. |
| **Duplicate Submissions & Race Conditions** | Network retries or double clicks causing multiple conflicting freight or supplier commitments. | **High** | Idempotency key tracking on `Decision.idempotency_key`. Exact re-submissions return `200 OK` replay. Conflicting parameter reuse returns `409 Conflict`. | Verified in `tests/api/test_decisions.py` and `tests/security/test_security_and_hardening.py`. |
| **Information Disclosure / Stack Trace Leaks** | Unhandled server exceptions or SQL errors leaking schema names, file paths, or credentials to public clients. | **Medium** | Global exception handlers in `app/main.py` formatting standardized error responses (`{ "error": { "code", "message", "request_id" } }`). Internal stack traces are logged securely server-side and never returned to the caller. | Verified in `tests/security/test_security_and_hardening.py`. |
| **Model Poisoning & Invalid Promotion** | Synthetic or corrupted feedback forcing promotion of degraded model artifacts. | **Critical** | Candidate models must pass independent validation on an evaluation holdout dataset (`ml/candidate_validation.py`). Must improve MAE by $\ge 3\%$ without exceeding secondary metric thresholds. Auto-promotion is disabled by default (`RETRAINING_AUTO_PROMOTION_ENABLED=false`). | Verified in `tests/ml/test_model_retraining.py` and `tests/e2e/test_full_system_lifecycle.py`. |

---

## 2. Authentication & Credential Architecture

1. **Password Hashing:**
   - Standard `bcrypt` password hashing with cost factor 12 (`bcrypt.gensalt(12)`).
   - Plaintext passwords are never persisted to disk or logged.
   - Verification implemented with constant-time password comparison (`bcrypt.checkpw`).

2. **JWT Access Tokens:**
   - Standard HS256 JSON Web Tokens (PyJWT).
   - Configurable token expiration (default 24 hours / 1440 minutes).
   - Token payload:
     ```json
     {
       "sub": "operator",
       "user_id": "usr_operator_01",
       "role": "OPERATOR",
       "email": "operator@supplyprescript.internal",
       "iat": 1730000000,
       "exp": 1730086400
     }
     ```

3. **System Roles & Permissions Matrix:**

| Role | Operational Scope | Assigned Permissions |
|---|---|---|
| `OPERATOR` | Supply chain operators & logistics coordinators | `read:operations`, `create:predictions`, `create:optimization`, `create:decisions`, `create:outcomes` |
| `ANALYST` | Business analysts & data science evaluators | `read:operations`, `read:analytics`, `create:predictions`, `create:optimization`, `create:dataset`, `evaluate:model` |
| `ADMIN` | Platform administrators & ML engineering leads | All operational, analytical, retraining, candidate promotion, and rollback capabilities (`admin:all`) |

---

## 3. Request Correlation & Auditability

- Every incoming HTTP request is assigned a unique `X-Request-ID` correlation identifier (format: `req-<16_hex_chars>`).
- If a client supplies `X-Request-ID`, it is preserved; otherwise, a cryptographically random identifier is generated.
- The `X-Request-ID` is echoed in all response headers and embedded within error payloads.
- Security response headers attached to all responses:
  - `X-Request-ID: req-...`
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`

---

## 4. Residual Risks & Staging Recommendations

1. **Secret Key Rotation:**
   - Default `AUTH_SECRET_KEY` in development must be overridden via environment variables or a key vault (e.g., AWS Secrets Manager, HashiCorp Vault) prior to production deployment.
2. **Rate Limiting:**
   - In high-throughput public environments, reverse-proxy rate limiting (e.g. Nginx `limit_req` or Cloudflare) should be placed in front of `POST /api/auth/token` to mitigate brute-force attempts.
3. **Database TLS:**
   - Ensure `DATABASE_URL` specifies `sslmode=require` or `sslmode=verify-full` when connecting to managed cloud databases (AWS RDS, Cloud SQL).
