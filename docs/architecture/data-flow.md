# Data Flow

## Ingestion → prediction → portals

```mermaid
flowchart LR
    subgraph Sources
        PH[Pharmacies<br/>stock · sales · orders]
        PCT[PCT<br/>national inventory · imports]
        SUP[Suppliers<br/>capacity · delays]
        EXT[External<br/>weather · epidemio · WHO]
    end

    PH & PCT & SUP & EXT -->|ingest API| VAL[ETL validation<br/>backend/app/etl]
    VAL -->|publish| MQ[(RabbitMQ<br/>ingest.events)]
    VAL --> PG[(PostgreSQL + PostGIS)]

    PG --> FEAT[Feature engineering<br/>ml/features.py]
    FEAT --> FC[Demand models<br/>XGB · LGBM · Prophet]
    FC --> SC[Shortage classifier<br/>+ SHAP]
    SC --> PG

    PG --> API[FastAPI]
    API --> CC[Command Center]
    API --> PP[Pharmacy Portal]
    API --> CP[Citizen Portal]

    SC -->|alerts| MQ2[(RabbitMQ<br/>alerts.fanout)]
    MQ2 --> W[Alert worker] --> NOTIF[Notifications]
```

## Batch scoring sequence

```mermaid
sequenceDiagram
    participant Cron as CronJob (02:00)
    participant Score as ml.score
    participant MLflow
    participant DB as PostgreSQL
    participant Cache as Redis

    Cron->>Score: run
    Score->>MLflow: load champion demand models + shortage clf
    Score->>DB: load latest sales / stock / imports / signals
    Score->>Score: build features → forecast → classify → SHAP
    Score->>DB: write forecasts, shortage_predictions, explanations
    Score->>DB: write recommendations + alerts
    Score->>Cache: invalidate cached views
```

## Time budget

| Stage | Cadence | Target |
|---|---|---|
| Ingestion | continuous / hourly batches | < 1s per batch |
| Feature build + train | weekly (or on drift) | < 10 min |
| Scoring refresh | nightly | < 5 min |
| API read (cached) | on demand | < 100 ms p95 |
