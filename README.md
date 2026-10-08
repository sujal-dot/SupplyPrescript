# SupplyPrescript

SupplyPrescript is an enterprise-grade prescriptive supply chain intelligence and analytics platform designed to model demand dynamics, optimize multi-echelon inventory, and provide actionable operational recommendations.

---

## Technology Stack

### Frontend
- **React** (v18)
- **Vite**
- **Tailwind CSS**
- **React Router** (v6)
- **Axios**

### Backend
- **FastAPI**
- **SQLAlchemy** (v2)
- **Pydantic** (v2)
- **PostgreSQL** (v16)
- **psycopg2-binary**
- **python-dotenv**

### Machine Learning
- **Pandas**
- **NumPy**
- **Scikit-learn**
- **XGBoost**
- **Joblib**

### Optimization
- **SciPy**
- **PuLP**

---

## Project Structure

```text
SupplyPrescript/
├── frontend/             # React + Vite frontend application
│   ├── src/
│   │   ├── components/   # Reusable UI components (Navbar, StatusCard)
│   │   ├── pages/        # Route pages (LandingPage, HealthPage)
│   │   ├── services/     # API service layer using Axios
│   │   ├── App.jsx       # Routing layout
│   │   └── main.jsx      # React entry point
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/routes/   # API endpoints (/health, /health/db)
│   │   ├── core/         # Settings and environment configuration
│   │   ├── database/     # SQLAlchemy connection and engine setup
│   │   └── main.py       # FastAPI application and CORS setup
│   ├── requirements.txt  # Backend Python dependencies
│   └── .venv/            # Local virtual environment
├── ml/                   # Machine learning pipelines and environments
│   ├── models/           # Trained models storage
│   ├── notebooks/        # Jupyter exploration notebooks
│   ├── scripts/          # ML preprocessing and training routines
│   └── requirements.txt  # ML package dependencies
├── optimization/         # Prescriptive optimization modeling
│   ├── models/           # Linear & integer programming models
│   ├── scripts/          # Optimization solving scripts
│   └── requirements.txt  # Optimization package dependencies
├── data/                 # Data storage tiers
│   ├── raw/              # Untransformed source inputs
│   ├── processed/        # Normalized & cleansed data
│   └── synthetic/        # Synthesized scenario datasets
├── database/             # Relational database setup
│   ├── migrations/       # Schema migration scripts
│   └── seeds/            # Initial database seed fixtures
├── tests/                # Automated tests
│   ├── backend/          # Backend API & DB integration tests
│   └── frontend/         # Frontend component tests
├── docs/                 # System architecture and API documentation
├── docker/               # Container support configurations
├── .env                  # Local environment variables
├── .env.example          # Environment variable template
├── .gitignore            # Git exclusions
├── docker-compose.yml    # PostgreSQL container definition
└── README.md             # Project documentation
```

---

## Local Setup

### 1. Database Setup

Start PostgreSQL in Docker with healthcheck and persistent volume:

```bash
docker compose up -d postgres
```

Verify the container is healthy:

```bash
docker compose ps
```

### 2. Backend Setup

Create virtual environment, install dependencies, and start the FastAPI server:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup

Install dependencies and start the Vite development server:

```bash
cd frontend
npm install
npm run dev
```

---

## Service URLs

| Service | URL |
| :--- | :--- |
| **Frontend** | [http://localhost:5173](http://localhost:5173) |
| **Backend** | [http://localhost:8000](http://localhost:8000) |
| **Swagger UI** | [http://localhost:8000/docs](http://localhost:8000/docs) |
| **ReDoc** | [http://localhost:8000/redoc](http://localhost:8000/redoc) |
| **PostgreSQL** | `localhost:5432` |

---

## API Documentation

Swagger Interactive UI:
[http://localhost:8000/docs](http://localhost:8000/docs)

OpenAPI Specification JSON:
[http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Available Endpoints

#### 1. Suppliers
- `GET /api/suppliers`
- **Pagination**: `page` (default 1, minimum 1), `page_size` (default 20, 1-100).
- **Filtering**:
  - `origin`: Filter by origin city (e.g. `?origin=Mumbai`)
  - `min_reliability`: Filter by minimum reliability (e.g. `?min_reliability=0.90`)
- **Example**:
  ```bash
  curl "http://localhost:8000/api/suppliers?page=1&page_size=20&origin=Mumbai&min_reliability=0.90"
  ```

#### 2. Shipments
- `GET /api/shipments`
- **Pagination**: `page` (default 1, minimum 1), `page_size` (default 50, 1-100).
- **Filtering**:
  - `supplier_id`: Filter by supplier ID (e.g. `?supplier_id=SUP001`)
  - `product_id`: Filter by product ID (e.g. `?product_id=PROD001`)
  - `priority`: Filter by priority (`Low`, `Medium`, `High`, `Critical`)
  - `transport_mode`: Filter by transport mode (`Road`, `Rail`, `Air`, `Sea`)
  - `is_delayed`: Filter by delay status (`true` or `false`)
  - `start_date` / `end_date`: Filter by `order_date` range (YYYY-MM-DD, e.g. `?start_date=2024-01-01&end_date=2024-03-31`)
- **Sorting**:
  - `sort_by`: Field allowlist (`order_date`, `quantity`, `shipping_cost`, `lead_time`, `delay_days`)
  - `sort_order`: Direction (`asc` or `desc`)
- **Example**:
  ```bash
  curl "http://localhost:8000/api/shipments?page=1&page_size=50&is_delayed=true&transport_mode=Road&sort_by=delay_days&sort_order=desc"
  ```

#### 3. Inventory
- `GET /api/inventory`
- **Pagination**: `page` (default 1, minimum 1), `page_size` (default 20, 1-100).
- **Filtering**:
  - `product_id`: Filter by product ID (e.g. `?product_id=PROD001`)
  - `inventory_status`: Filter by status (`Healthy`, `Low`, `Critical`, `Out of Stock`)
- **Example**:
  ```bash
  curl "http://localhost:8000/api/inventory?page=1&page_size=20&inventory_status=Critical"
  ```

#### 4. Dashboard
- `GET /api/dashboard`
- **Description**: Returns database-aggregated supply-chain KPIs, status breakdowns, and top delayed suppliers computed directly inside PostgreSQL.
- **Example**:
  ```bash
  curl "http://localhost:8000/api/dashboard"
  ```

---

## Running Tests

Run the full automated test suite:

```bash
pytest -v
```

Or target specific modules:

```bash
pytest tests/api -v         # Day 5 API endpoints test suite
pytest tests/backend -v     # Health and DB connectivity
pytest tests/database -v    # Day 4 Database schema & relationships
pytest tests/data -v        # Day 3 Data cleaning pipeline
pytest tests/test_dataset.py -v # Day 2 Synthetic dataset integrity
```

