 ML Platform — End-to-End Churn Prediction System

[![CI - Lint & Test](https://github.com/Deepinalama/ml-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/Deepinalama/ml-platform/actions/workflows/ci.yml)


-A production-style Machine Learning platform built with **Apache Airflow**, **FastAPI**, **Django REST Framework**, and **PostgreSQL** — all containerized with **Docker Compose**.

---


---

 Tech Stack

| Layer | Technology |
|---|---|
| **Orchestration** | Apache Airflow 2.9 |
| **ML Inference API** | FastAPI + Uvicorn |
| **Control Plane API** | Django REST Framework + SimpleJWT |
| **ML Model** | Scikit-learn (Random Forest Classifier) |
| **Database** | PostgreSQL 15 |
| **Containerization** | Docker Compose |
| **Data Processing** | Pandas, Faker |

---

 Project Structure

```
ml-platform/
├── .github/
│   └── workflows/
│       └── ci.yml                # CI: lint + test for all 3 services
├── docker-compose.yml
├── .env
├── postgres/
│   ├── init.sql                  # 5-table schema
│   └── 00_create_airflow_db.sql
├── airflow/
│   ├── dags/
│   │   └── churn_pipeline_dag.py # 4-task DAG
│   ├── Dockerfile
│   └── requirements.txt
├── fastapi_app/
│   ├── main.py                   # Inference service
│   ├── Dockerfile
│   └── requirements.txt
├── django_app/
│   ├── core/                     # Settings, URLs
│   ├── accounts/                 # Registration
│   ├── pipelines/                # Models, Views, Serializers
│   ├── manage.py
│   ├── Dockerfile
│   └── requirements.txt
└── shared/
    └── model_storage/            # Shared .pkl volume
```

---

 Database Schema

| Table | Purpose |
|---|---|
| `raw_customers` | Raw ingested customer data |
| `features` | Cleaned and engineered features for ML |
| `model_versions` | ML model registry (accuracy, file path, active status) |
| `predictions` | Log of every prediction made by FastAPI |
| `pipeline_runs` | Airflow DAG run history |

---

Airflow Pipeline (DAG)

The `churn_prediction_pipeline` DAG runs daily with 4 tasks:

```
fetch_data → transform_features → train_model → register_model
```

- **fetch_data** — Generates 200 synthetic customer records and writes to `raw_customers`
- **transform_features** — Converts raw data to numeric features and writes to `features`
- **train_model** — Trains a Random Forest classifier, saves `.pkl` to shared volume
- **register_model** — Registers model metadata in `model_versions`, marks it active

---
 FastAPI Endpoints

Base URL: `http://localhost:8000`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check + model loaded status |
| `GET` | `/model-info` | Active model version info |
| `POST` | `/predict` | Predict churn for a customer |
| `POST` | `/reload-model` | Reload latest active model |

 Sample Predict Request
```json
POST /predict
{
  "customer_id": "customer-001",
  "days_since_signup": 365,
  "days_since_last_login": 60,
  "avg_monthly_spend": 15.0,
  "support_ticket_count": 8,
  "is_premium": false,
  "requested_by": "api"
}
```

 Sample Response
```json
{
  "customer_id": "customer-001",
  "will_churn": true,
  "probability": 0.93,
  "model_version": "churn_model_v1.pkl"
}
```

---

 Django REST API + JWT

Base URL: `http://localhost:8001`

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/api/auth/register/` | None | Register new user |
| `POST` | `/api/auth/login/` | None | Login, get JWT tokens |
| `POST` | `/api/auth/refresh/` | None | Refresh access token |
| `GET` | `/api/models/` | JWT | List all model versions |
| `GET` | `/api/predictions/` | JWT | List prediction history |
| `GET` | `/api/pipeline-runs/` | JWT | List pipeline run history |
| `POST` | `/api/trigger-retrain/` | JWT (Admin) | Trigger Airflow DAG manually |

 JWT Flow
```
POST /api/auth/login/ → { access: "eyJ...", refresh: "eyJ..." }
GET  /api/models/     → Authorization: Bearer eyJ...
```

---

 Running the Project

  Running Tests & CI

This project uses GitHub Actions to automatically lint and test all three services (`django_app`, `fastapi_app`, `airflow`) on every push and pull request to `main`/`develop`.

What CI checks
- **Lint** — `ruff` (code issues), `black` (formatting), `isort` (import order)
- **Test** — `pytest` for Django and FastAPI
- **Airflow DAGs** — validates that all DAG files compile without syntax errors

Running checks locally

Each service has its own virtual environment and dependencies. Example for Django:

\`\`\`bash
cd django_app
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
pip install pytest pytest-django ruff black isort

ruff check .
black --check .
isort --check-only .
python manage.py check
pytest
\`\`\`

Repeat the same pattern inside `fastapi_app/` (using `pytest` + `httpx` instead of `pytest-django`).

 Auto-fixing formatting issues
\`\`\`bash
isort .
black .
\`\`\`

Prerequisites
- Docker Desktop
- Docker Compose

 1. Clone the repo
```bash
git clone https://github.com/Deepinalama/ml-platform.git
cd ml-platform
```

2. Set up environment variables
```bash
# Edit .env with your values
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=ml_platform
POSTGRES_PORT=5432
AIRFLOW_DB=airflow_meta
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=admin123
AIRFLOW_FERNET_KEY=your_fernet_key
AIRFLOW_SECRET_KEY=your_secret_key
DJANGO_SECRET_KEY=your_django_secret
```

3. Start all services
```bash
docker-compose up -d --build
```

 4. Run Django migrations and create superuser
```bash
docker exec -it ml_platform_django python manage.py migrate
docker exec -it ml_platform_django python manage.py createsuperuser
```

 5. Set up Airflow Postgres connection
- Go to `http://localhost:8080` (Airflow UI)
- Admin → Connections → Add
- Connection Id: `ml_platform_postgres`, Type: `Postgres`, Host: `postgres`, Port: `5432`

 6. Trigger the pipeline
- In Airflow UI, trigger `churn_prediction_pipeline` manually
- Watch all 4 tasks turn green

 7. Test the APIs
- FastAPI Swagger UI: `http://localhost:8000/docs`
- Django REST API: `http://localhost:8001/api/auth/login/`

---

 🔗 Services

| Service | URL |
|---|---|
| Airflow UI | http://localhost:8080 |
| FastAPI Swagger | http://localhost:8000/docs |
| Django REST API | http://localhost:8001 |
| PostgreSQL | localhost:5432 |
