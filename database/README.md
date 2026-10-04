# Database Management

This directory manages database migrations, schema definitions, and seed data for the SupplyPrescript platform.

## Directory Structure

```text
database/
├── migrations/   # Schema migrations (Alembic or SQL scripts)
├── seeds/        # Initial reference data and synthetic benchmark seeds
└── README.md
```

## Configuration

PostgreSQL runs via Docker:

- **Host**: `localhost`
- **Port**: `5432`
- **Database**: `supplyprescript`
- **User**: `supplyprescript`
- **Password**: configured in `.env`

Connection string format:
```text
DATABASE_URL=postgresql+psycopg2://supplyprescript:supplyprescript@localhost:5432/supplyprescript
```
