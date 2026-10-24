# SupplyPrescript — REST API Specification & Reference

**Phase:** Phase 8 — Production Polish  
**Version:** 1.0.0  
**Base URL:** `http://localhost:8000/api`  
**OpenAPI Specification:** Available at `http://localhost:8000/docs` (Swagger UI)  

---

## 1. Global Conventions & Standards

### 1.1 Headers
All requests should supply the following headers:
| Header | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `Content-Type` | `string` | Must be `application/json` for requests with a payload. | Yes |
| `Authorization` | `string` | Standard Bearer token: `Bearer <jwt_token>`. | When `AUTH_REQUIRED=true` or accessing restricted endpoints |
| `X-Request-ID` | `string` | Unique client correlation ID (e.g., `req-abc12345`). If omitted, the gateway generates one automatically. | Optional |

### 1.2 Standard Error Response Envelope
All non-2xx responses conform to a unified error structure:
```json
{
  "error": {
    "code": "VALIDATION_ERROR | NOT_FOUND | FORBIDDEN | UNAUTHORIZED | IDEMPOTENCY_CONFLICT | INTERNAL_ERROR",
    "message": "Human-readable explanation of error.",
    "request_id": "req-9a02459984db4d16",
    "details": []
  }
}
```

---

## 2. Authentication & User Identity

### `POST /api/auth/token`
Authenticates a user and issues an HMAC-SHA256 JSON Web Token.

- **Request Body:**
  ```json
  {
    "username": "operator",
    "password": "Operator123!"
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "role": "OPERATOR",
    "expires_in_minutes": 1440
  }
  ```

### `GET /api/auth/me`
Retrieves currently authenticated user claims and permissions.
- **Required Role:** Any active authenticated user (`OPERATOR`, `ANALYST`, `ADMIN`).

---

## 3. Operational Shipments

### `GET /api/shipments`
Retrieves paginated operational shipments with filtering.
- **Query Parameters:** `page`, `page_size`, `supplier_id`, `priority`, `origin`, `destination`.
- **Response `200 OK`:**
  ```json
  {
    "data": [
      {
        "shipment_id": "SHIP000001",
        "supplier_id": "SUP001",
        "product_id": "PROD001",
        "quantity": 500,
        "lead_time": 14,
        "priority": "High"
      }
    ],
    "total": 15000,
    "page": 1,
    "page_size": 50,
    "total_pages": 300
  }
  ```

### `POST /api/shipments`
Ingests a new shipment into the operational store.
- **Required Role:** `OPERATOR`, `ADMIN`.
- **Request Body:**
  ```json
  {
    "shipment_id": "SHIP-DEMO-001",
    "supplier_id": "SUP001",
    "product_id": "PROD001",
    "origin": "Shenzhen",
    "destination": "Chicago",
    "order_date": "2026-10-01",
    "expected_delivery_date": "2026-10-15",
    "lead_time": 14,
    "quantity": 1000,
    "unit_cost": "35.00",
    "shipping_cost": "4500.00",
    "supplier_reliability": "0.94",
    "inventory_level": 200,
    "demand": 800,
    "priority": "Critical",
    "transport_mode": "Road"
  }
  ```
- **Response `201 Created`:** Returns created shipment entity.
- **Response `404 Not Found`:** Returned if `supplier_id` or `product_id` does not exist.

### `GET /api/shipments/{shipment_id}`
Retrieves a single shipment by its business identifier.
- **Response `200 OK`:** Returns shipment record.
- **Response `404 Not Found`:** Returned if shipment does not exist.

---

## 4. Machine Learning Inference

### `POST /api/predict`
Executes dual XGBoost prediction pipeline for delay probability and duration.
- **Request Body:**
  ```json
  {
    "supplier_id": 1,
    "product_id": 1,
    "quantity": 1000,
    "inventory_level": 200,
    "transport_mode": "Road",
    "destination": "Chicago",
    "priority": "Critical",
    "lead_time": 14
  }
  ```
- **Response `200 OK`:**
  ```json
  {
    "delay_probability": 0.157,
    "risk_category": "High",
    "predicted_delay_days": 1.76,
    "model_version": "v1.0",
    "prediction_timestamp": "2026-10-24T11:45:00Z"
  }
  ```

---

## 5. Prescriptive Decisions & Write-Back

### `POST /api/decisions`
Commits an authorized prescriptive decision into PostgreSQL with idempotency guarantees.
- **Required Role:** `OPERATOR`, `ADMIN`.
- **Request Body:**
  ```json
  {
    "shipment_id": "SHIP-DEMO-001",
    "option_id": "A",
    "recommendation": "AIR_FREIGHT",
    "idempotency_key": "idem-key-9888606f3ba5",
    "notes": "Air Freight chosen to prevent stockout under high lead time delay."
  }
  ```
- **Response `201 Created`:** Decision created.
  ```json
  {
    "decision_id": "DEC-EXEC-11A0AA54",
    "shipment_id": "SHIP-DEMO-001",
    "status": "RECORDED",
    "idempotency_key": "idem-key-9888606f3ba5",
    "authorized_by": "operator",
    "created_at": "2026-10-24T11:45:00Z"
  }
  ```
- **Response `200 OK` (Replay):** Exact replay with identical key and parameters returns existing record without duplicating entries.
- **Response `409 Conflict`:** Returned if `idempotency_key` is reused with conflicting decision parameters.

### `GET /api/decisions`
Lists historical decisions with filtering by `shipment_id`, `status`, or date range.

### `GET /api/decisions/{decision_id}`
Retrieves a specific decision with its recommendation snapshots and status.

---

## 6. Actual Outcomes & Decision ROI

### `POST /api/decisions/{decision_id}/outcome`
Ingests physical delivery actuals and executes closed-loop variance comparison.
- **Required Role:** `OPERATOR`, `ADMIN`.
- **Request Body:**
  ```json
  {
    "actual_cost": 44050.00,
    "currency": "USD",
    "actual_delivery_date": "2026-11-03",
    "actual_delay_days": 1,
    "actual_delay": 1.0,
    "actual_supplier": "SUP001",
    "actual_quantity": 1000,
    "outcome_status": "DELIVERED",
    "notes": "Delivered on time with zero stockout."
  }
  ```
- **Response `201 Created`:** Returns outcome record and variance analysis:
  ```json
  {
    "outcome_id": "OUT-20261024-C44CB9",
    "decision_id": "DEC-EXEC-11A0AA54",
    "variance": {
      "cost_variance": 8927.50,
      "delay_variance": -0.52,
      "quantity_variance": 0.0,
      "supplier_matched": true
    },
    "data_completeness": "COMPLETE"
  }
  ```

### `GET /api/decisions/{decision_id}/roi`
Calculates comprehensive ROI, financial savings, and decision success.
- **Response `200 OK`:**
  ```json
  {
    "decision_id": "DEC-EXEC-11A0AA54",
    "cost": {
      "predicted_cost": "35122.50",
      "actual_cost": "44050.00",
      "cost_difference": "8927.50",
      "money_saved_vs_baseline": "-4550.00"
    },
    "delay": {
      "predicted_delay": 1.52,
      "actual_delay": 1.0,
      "delay_difference": -0.52
    },
    "decision_evaluation": {
      "decision_success": "PARTIAL_SUCCESS",
      "success_score": 0.85,
      "summary_explanation": "Stockout was prevented; minor cost overrun from expedited handling."
    },
    "roi": {
      "status": "CALCULATED",
      "roi_percentage": 145.2,
      "reason": "Net stockout penalty avoided outweighs expedited air freight investment."
    }
  }
  ```

### `GET /api/roi/dashboard`
Returns portfolio-level ROI aggregations, success rates, and strategy comparisons.

---

## 7. Model Feedback & Continuous Learning

### `POST /api/feedback/generate`
Scans for newly completed outcomes and builds verified feedback observations.
- **Required Role:** `ANALYST`, `ADMIN`.
- **Response `200 OK`:**
  ```json
  {
    "status": "SUCCESS",
    "dataset_version": "feedback_v20261024_114500",
    "total_feedback_records": 124,
    "eligible_count": 118,
    "excluded_count": 6
  }
  ```

### `POST /api/feedback/evaluate`
Calculates historical accuracy metrics (MAE, RMSE, Mean Signed Error) for a model version.
- **Required Role:** `ANALYST`, `ADMIN`.
- **Request Body:** `{"model_version": "v1.0"}`
- **Response `200 OK`:**
  ```json
  {
    "model_version": "v1.0",
    "sample_count": 118,
    "mae": 0.842,
    "rmse": 1.140,
    "mean_signed_error": -0.125
  }
  ```

### `GET /api/ml/retraining/monitor`
Monitors active production model for performance degradation or concept drift.
- **Required Role:** `ANALYST`, `ADMIN`.
- **Response `200 OK`:**
  ```json
  {
    "status": "HEALTHY",
    "is_degraded": false,
    "active_version": "v1.0",
    "baseline_mae": 0.842,
    "current_feedback_mae": 0.890,
    "degradation_percentage": 5.7
  }
  ```

### `POST /api/ml/retraining/run`
Triggers candidate model retraining and validation.
- **Required Role:** `ADMIN`.
- **Request Body:** `{"force": true, "trigger_reason": "Performance drift detected"}`
- **Response `200 OK`:**
  ```json
  {
    "job_id": "RETRAIN_20261024_7C342C",
    "status": "REGISTERED",
    "message": "Candidate model passed validation gate (MAE improved by 4.2%)."
  }
  ```

### `POST /api/ml/retraining/jobs/{job_id}/promote`
Promotes a validated candidate model to active production status.
- **Required Role:** `ADMIN` (Requests with `OPERATOR` role rejected with HTTP 403 Forbidden).

### `POST /api/ml/retraining/rollback`
Executes an immediate rollback to a designated target model version.
- **Required Role:** `ADMIN`.
- **Request Body:** `{"target_version": "v1.0"}`
- **Response `200 OK`:**
  ```json
  {
    "status": "ROLLED_BACK",
    "active_version": "v1.0",
    "timestamp": "2026-10-24T11:45:00Z"
  }
  ```
