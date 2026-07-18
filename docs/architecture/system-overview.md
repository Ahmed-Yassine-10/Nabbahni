# SentinelleRx — System Overview

SentinelleRx is a national medication-shortage prediction platform for Tunisia.
It ingests supply-chain data, forecasts demand, predicts shortages with
explainable AI, and serves professionally-validated recommendations through
three role-based portals.

## C4 — Context

```mermaid
graph TB
    subgraph Actors
        PCT[PCT Administrators]
        RHA[Regional Health Authorities]
        HP[Hospital Pharmacists]
        CP[Community Pharmacies]
        SUP[Suppliers / Importers]
        CIT[Citizens / Patients]
    end

    SRX([SentinelleRx Platform])

    PCT --> SRX
    RHA --> SRX
    HP --> SRX
    CP --> SRX
    SUP --> SRX
    CIT --> SRX

    SRX -. external signals .-> EXT[Weather · Epidemiology · WHO · Ministry · Ports]
    SRX -. identity .-> KC[Keycloak OIDC]
```

## C4 — Containers

```mermaid
graph LR
    subgraph Frontend
        WEB[Next.js 15 App<br/>Command Center · Pharmacy · Citizen]
    end

    subgraph Backend
        API[FastAPI API]
        WORKER[Alert Worker]
        ETL[ETL / Data Hub]
    end

    subgraph ML
        TRAIN[Training<br/>XGBoost · LightGBM · Prophet]
        SCORE[Scoring + SHAP]
        MLF[(MLflow Registry)]
    end

    subgraph Data
        PG[(PostgreSQL + PostGIS)]
        REDIS[(Redis)]
        MQ[(RabbitMQ)]
        S3[(MinIO / S3)]
        QDR[(Qdrant)]
    end

    WEB -->|REST /api/v1| API
    API --> PG
    API --> REDIS
    API -->|publish| MQ
    MQ --> WORKER
    WORKER --> PG
    ETL --> PG
    TRAIN --> MLF
    TRAIN --> PG
    SCORE --> MLF
    SCORE --> PG
    MLF --> S3
    API -. auth .-> KC[Keycloak]
    API --> QDR
```

## Module map

| # | Module | Where it lives |
|---|---|---|
| 1 | National Data Hub (ETL) | `backend/app/etl`, ingestion endpoints, RabbitMQ |
| 2 | Demand Forecasting AI | `ml/ml/training`, `ml/ml/features.py` |
| 3 | Shortage Prediction Engine | `ml/ml/shortage.py`, `ml/ml/score.py` |
| 4 | Explainable AI | `ml/ml/explain.py` (SHAP → FR/AR narrative) |
| 5 | Smart Recommendations | `backend/app/services/recommendations.py` |
| 6 | Substitution Engine | `backend/app/services/substitution.py` |
| 7 | National Command Center | `frontend/src/app/[locale]/cc` |
| 8 | Pharmacy Portal | `frontend/src/app/[locale]/pharmacy` |
| 9 | Citizen Portal | `frontend/src/app/[locale]/(page + medication)` |

## Design principles

- **Explainability first** — every shortage prediction stores a SHAP-derived
  rationale; no black-box decisions reach a user.
- **Human-in-the-loop** — recommendations and substitutions are decision-support;
  a PCT officer or pharmacist validates the final action.
- **Explain at write time** — SHAP runs during scoring, never in the request path.
- **One schema, three consumers** — API, ML, and the seeder share the SQLAlchemy
  models in `backend/app/models`.
