# SupplyPrescript Test Suite

This directory contains the automated test suites for SupplyPrescript.

## Structure

```text
tests/
├── backend/
│   ├── __init__.py
│   └── test_api.py      # Tests for FastAPI endpoints and DB connectivity
├── frontend/
│   ├── __init__.py
│   └── ...              # Frontend component/integration tests
└── README.md
```

## Running Backend Tests

Ensure PostgreSQL is running in Docker and virtual environment is activated:

```bash
# From workspace root
source backend/.venv/bin/activate
pytest tests/backend -v
```

Or directly via python:

```bash
backend/.venv/bin/pytest tests/backend -v
```
