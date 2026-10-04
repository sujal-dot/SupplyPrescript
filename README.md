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

## Running Tests

Run the backend integration and health check test suite:

```bash
source backend/.venv/bin/activate
pytest tests/backend -v
```
