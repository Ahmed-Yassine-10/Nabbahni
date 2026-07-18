# SentinelleRx 🇹🇳

**La météo des médicaments de Tunisie** — an AI platform that predicts medication
shortages *before* they reach patients, and turns supply-chain data into
**explainable**, professionally-validated procurement recommendations.

> Built for national deployment: PCT (Pharmacie Centrale de Tunisie), regional
> health authorities, hospital & community pharmacies, suppliers, and citizens.

---

## What it does

```
 Pharmacies ─┐
 PCT ────────┤   ETL     ┌───────────┐   ┌──────────────────┐   ┌───────────────┐
 Suppliers ──┼──────────▶│  Data Hub │──▶│ Demand Forecast  │──▶│ Shortage       │
 External ───┘  (queue)  │ Postgres  │   │ XGB / LGBM /     │   │ Prediction +   │
                         │ + PostGIS │   │ Prophet          │   │ SHAP explain   │
                         └───────────┘   └──────────────────┘   └───────┬───────┘
                                                                        │
                    ┌──────────────────┬───────────────────────────────┤
                    ▼                  ▼                                ▼
         National Command    Pharmacy Portal                  Citizen Portal
         Center (heatmap)    (orders, substitutions)          (search, availability)
```

Nine modules: National Data Hub · Demand Forecasting AI · Shortage Prediction
Engine · Explainable AI · Smart Recommendations · Medication Substitution ·
National Command Center · Pharmacy Portal · Citizen Portal.

### Where the data surfaces

| Question | Screen |
|---|---|
| What's at risk nationally? | `/cc` — choropleth + risk board + KPI strip |
| How much stock do we hold, and for how long? | `/cc/stock` — coverage distribution, inventory value, worst covers |
| Why did the model say that? | `/cc/medications/[id]` — forecast + SHAP factor chart + French rationale |
| Which model is in production, and is it any good? | `/cc/models` — champions per horizon, WAPE/MAPE/RMSE, all runs |
| What should we do about it? | `/cc/recommendations` — proposals with cost, confidence, validate/reject |
| What's running out on my shelf? | `/pharmacy` — stock sorted by urgency, days of cover |
| Can I get this medicine? | `/` — public search, availability by governorate, alternatives |

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15 (App Router), React, TypeScript, Tailwind, shadcn/ui, MapLibre GL |
| Backend | FastAPI, Python 3.12, SQLAlchemy 2, Alembic, Pydantic v2 |
| Data | PostgreSQL + PostGIS, Redis, RabbitMQ, MinIO (S3), Qdrant |
| ML | XGBoost, LightGBM, Prophet, SHAP, MLflow |
| Auth | Keycloak (OIDC, RBAC, MFA) |
| Observability | Prometheus, Grafana, OpenTelemetry, Alertmanager, Sentry |
| DevOps | Docker, Kubernetes (kustomize), GitHub Actions |

## Repository layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI service — API, models, ETL, workers |
| `ml/` | Feature engineering, model training, scoring, explainability |
| `data-generator/` | Realistic synthetic Tunisian dataset seeder |
| `frontend/` | Next.js app with three role-based portals (fr/ar) |
| `infra/` | docker-compose configs, Keycloak realm, k8s, monitoring |
| `docs/` | Architecture diagrams, ERD, security, roadmaps |

---

## Quickstart — Windows (no Docker needed) ⚡

The fastest way to run the whole platform locally. Requires only **Python 3.12+**
and **Node.js 20+** on your PATH.

```
git clone https://github.com/Ahmed-Yassine-10/Nabbahni.git
cd Nabbahni
run.bat
```

**First run takes 8–12 minutes** and needs no further input: virtualenv →
Python packages → database → synthetic dataset → scoring → frontend build.
Every later `run.bat` starts in under a minute.

Model training — normally the 10–20 minute step — is skipped because the
trained champions ship in [`ml/artifacts/`](ml/artifacts/README.md). They are
trained on **synthetic** data: a convenience for running the demo, not
validated models. Delete that folder to force a full retrain.

> New contributor? Read **[CONTRIBUTING.md](CONTRIBUTING.md)** — it covers the
> first-run timeline step by step, where runtime state lives, and the gotchas
> that will otherwise cost you an hour.

Once up, it launches:

| | |
|---|---|
| 🌍 Web app | http://localhost:3000 (opens automatically) |
| 📘 API docs | http://localhost:8000/docs |

Log in with the **role dropdown** (top-right). Each role lands on its own portal
with its own navigation, density and accent colour:

| Role | Lands on | Sees |
|---|---|---|
| Admin PCT | `/cc` | Everything: map, stocks, recommendations, model governance |
| Autorité régionale | `/cc` | Same minus model governance & supply chain |
| Pharmacien (officine / hôpital) | `/pharmacy` | Own stock, suggested orders, substitutions |
| Fournisseur | `/cc/supply-chain` | Delivery commitments + alerts |
| Citoyen | `/` | Public search (no login needed) |

> **Upgrading an existing install?** Governorate boundaries and the scoring
> outputs changed. Delete `%LOCALAPPDATA%\SentinelleRx` and re-run `run.bat`
> for a clean rebuild, or re-run `make seed && make train && make score`.

| Script | Purpose |
|---|---|
| `run.bat` | Set up (first time) + launch API and web |
| `setup.bat` | Setup only (venv, deps, database, seed, models, frontend) |
| `stop.bat` | Stop both services |

**How it works**: this mode runs on **SQLite** with Keycloak/Redis/RabbitMQ/MLflow
gracefully disabled, so no infrastructure is required. Runtime files (virtualenv,
database, frontend `node_modules`) live in `%LOCALAPPDATA%\SentinelleRx` —
deliberately **outside OneDrive**, whose file syncing corrupts `node_modules` and
makes installs very slow. Delete that folder to force a clean rebuild.

> For the full production stack (PostgreSQL + PostGIS, Keycloak, Redis, RabbitMQ,
> MLflow, Prometheus/Grafana), use the Docker Compose path below.

---

## Quickstart — full stack (Docker)

### Prerequisites
- Docker Desktop
- Python 3.12 + [uv](https://github.com/astral-sh/uv) (or plain `pip`)
- Node.js 20+

### 1. Configure
```bash
cp .env.example .env
```

### 2. Start infrastructure
```bash
docker compose up -d          # postgres, redis, rabbitmq, keycloak, minio, qdrant, mlflow, monitoring
docker compose ps             # wait until healthy
```
Keycloak auto-imports the `sentinellerx` realm (6 roles, demo users, MFA policy).

### 3. Backend + database
```bash
cd backend
uv sync                       # or: pip install -e .
alembic upgrade head          # create all tables
```

### 4. Seed + train + score
```bash
# from repo root
make seed      # ~150 medications, 24 governorates, ~230 pharmacies, 2y history
make train     # trains XGBoost/LightGBM/Prophet per horizon, registers champions in MLflow
make score     # writes forecasts, shortage predictions, explanations, recommendations, alerts
```

### 5. Run the apps
```bash
make api       # FastAPI  -> http://localhost:8000/docs
make worker    # alert fan-out worker (separate terminal)
cd frontend && npm install && npm run dev   # -> http://localhost:3000
```

### Demo logins (Keycloak)
| Role | Username | Password |
|---|---|---|
| PCT Admin | `admin@pct.tn` | `Sentinelle2026!` |
| Regional Authority | `region.tunis@sante.tn` | `Sentinelle2026!` |
| Hospital Pharmacist | `hopital.charlesnicolle@sante.tn` | `Sentinelle2026!` |
| Community Pharmacist | `pharmacie.elmanar@pharma.tn` | `Sentinelle2026!` |
| Supplier | `supplier.medis@medis.tn` | `Sentinelle2026!` |
| Citizen | `citoyen@demo.tn` | `Sentinelle2026!` |

> Dev credentials only — never ship these to production.

---

## Windows / PowerShell notes

The `Makefile` targets are thin wrappers. If `make` is unavailable, run the
equivalent commands directly:

```powershell
docker compose up -d
cd backend; alembic upgrade head
cd ..\data-generator; python -m generator.seed --seed 42
cd ..\ml; python -m ml.train_all; python -m ml.score
cd ..\backend; uvicorn app.main:app --reload --port 8000
cd ..\frontend; npm run dev
```

**OneDrive**: this repo lives under a synced OneDrive folder. `node_modules/`
and `.venv/` are git-ignored; heavy dev churn under OneDrive can be slow — pause
sync or relocate the working copy if builds feel sluggish.

**Prophet**: installs from a prebuilt wheel on Python 3.12. If it fails to build
locally, training skips Prophet gracefully and logs a note (XGBoost/LightGBM
still run); or run training inside the `ml` Docker image.

---

## Service endpoints (local)

| Service | URL |
|---|---|
| API + OpenAPI docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Keycloak | http://localhost:8081 (`admin` / `admin`) |
| MLflow | http://localhost:5000 |
| RabbitMQ mgmt | http://localhost:15672 |
| MinIO console | http://localhost:9001 |
| Grafana | http://localhost:3001 (`admin` / `admin`) |
| Prometheus | http://localhost:9090 |

## Documentation

- [System overview](docs/architecture/system-overview.md)
- [Data flow](docs/architecture/data-flow.md)
- [AI architecture](docs/architecture/ai-architecture.md)
- [Deployment & DR](docs/architecture/deployment.md)
- [Database ERD](docs/database/ERD.md)
- [Security (OWASP / RBAC / GDPR)](docs/security/)
- [Roadmaps & launch strategy](docs/roadmap/)

## Safety & governance

Every shortage prediction is **explainable** (SHAP → human-readable French/Arabic
rationale). Recommendations and substitutions are **decision-support only** — a
pharmacist or PCT officer always validates the final action. No black-box calls.
