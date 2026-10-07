# Database Management — SupplyPrescript

This directory contains the database migration scripts, DDL schema, seeds, and loading pipelines for the **SupplyPrescript** platform.

The persistence layer runs on **PostgreSQL** and uses **SQLAlchemy 2.0 ORM** with **Alembic** for schema migrations and versioning.

---

## 1. Architecture & Workflow

The database schema models the end-to-end prescriptive supply chain lifecycle:

```text
Suppliers (1)
   │
   └──< Shipments (N)
           │
           └──< Predictions (N)
                   │
                   └──< Recommendations (N)
                           │
                           └──< Decisions (N)
                                   │
                                   └──< Outcomes (N)
```

Additionally:
- `products (1) ──< shipments (N)`
- `products (1) ──< inventory (N)`
- `model_versions (1) ──< predictions (N)`

---

## 2. Database Tables Overview

The schema is composed of **9 normalized tables**:

| Table | Description | Primary Key | Key Foreign Keys |
|---|---|---|---|
| `suppliers` | Master data of supply partners, origins, reliability scores, and capacities | `id` (SERIAL) | None (`supplier_id` unique) |
| `products` | Product catalog with categorization, unit costs, weights, and baseline demands | `id` (SERIAL) | None (`product_id` unique) |
| `shipments` | Central log of historical and scheduled shipments, logistics costs, and delays | `id` (SERIAL) | `supplier_id` &rarr; `suppliers.supplier_id`<br>`product_id` &rarr; `products.product_id` |
| `inventory` | Periodic inventory snapshots, demand rates, safety stocks, and health statuses | `id` (SERIAL) | `product_id` &rarr; `products.product_id` |
| `model_versions` | Registry of machine learning models, algorithms, dataset versions, and JSONB metrics | `id` (SERIAL) | None (`model_name, version` unique) |
| `predictions` | ML model inference outputs (e.g., delay risk, delivery duration, shortage alerts) | `id` (SERIAL) | `shipment_id` &rarr; `shipments.shipment_id`<br>`model_version_id` &rarr; `model_versions.id` |
| `recommendations` | Prescriptive mitigation recommendations generated from model predictions | `id` (SERIAL) | `prediction_id` &rarr; `predictions.id` |
| `decisions` | Operational decisions taken by human operators, AI agents, or business rules | `id` (SERIAL) | `recommendation_id` &rarr; `recommendations.id` |
| `outcomes` | Closed-loop feedback capturing actual delivery, cost, and effectiveness scores | `id` (SERIAL) | `decision_id` &rarr; `decisions.id` |

---

## 3. Referential Integrity & Cascade Behavior

To protect historical supply chain records against accidental data loss:
- **Foreign Key Deletion Policy**: `RESTRICT` is applied across all core tables and audit trails (`shipments`, `predictions`, `recommendations`, `decisions`, `outcomes`).
- Deleting an upstream master record (such as a `Supplier` or `Product`) that possesses downstream shipment history is rejected at the database engine level.
- Core business identifiers (`supplier_id`, `product_id`, `shipment_id`, `prediction_id`, `recommendation_id`, `decision_id`, `outcome_id`) are unique and indexed for fast querying.

---

## 4. Database Setup & Migrations

### Prerequisites

Ensure PostgreSQL is running (e.g. via Docker):

```bash
docker compose up -d postgres
```

The database configuration is loaded automatically from `.env` using `DATABASE_URL`. Do not hardcode credentials.

### Run Migrations

To apply the latest database migrations:

```bash
# From repository root:
alembic upgrade head

# Or from backend directory:
cd backend
source .venv/bin/activate
alembic upgrade head
```

### Rollback Migrations

To safely downgrade or revert migrations:

```bash
# Roll back the single most recent migration:
alembic downgrade -1

# Roll back all migrations to clean base state:
alembic downgrade base
```

---

## 5. Seeding Data

### A. Development Seed (Representative Sample)

To populate a small representative development dataset (~10 suppliers, 20 products, 50 shipments, 20 inventory records, 2 model versions, and a complete end-to-end workflow chain):

```bash
python database/seeds/seed_database.py
```

This script is fully idempotent and safe to run multiple times without creating duplicate records.

### B. Full Processed Dataset Import

To load the full processed dataset (`data/processed/shipments_processed.csv`, ~15,000 records) into PostgreSQL:

```bash
python database/seeds/load_processed_shipments.py
```

Features:
- Validates supplier and product master records.
- Automatically inserts missing master data references.
- Inserts shipments in batches of 1,000 for high performance.
- Skips existing shipment IDs to preserve data integrity and prevent duplicates.

---

## 6. Verifying Database Health

The backend provides a database connectivity health check:

```bash
curl http://localhost:8000/health/db
```

Expected response:

```json
{
  "status": "healthy",
  "database": "connected"
}
```

---

## 7. Automated Testing

All schema constraints, foreign key cascades, and ORM relationship chains are covered by automated tests:

```bash
pytest tests/database/ -v
```
