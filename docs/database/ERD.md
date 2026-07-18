# Database — Entity Relationship Diagram

PostgreSQL 16 + PostGIS. UUID primary keys, `created_at` / `updated_at` audit
columns, FK indexes, and composite indexes on time-series query paths. The
canonical definitions live in `backend/app/models/`.

```mermaid
erDiagram
    atc_classes ||--o{ atc_classes : parent
    medications }o--|| atc_classes : "atc_code (label ref)"
    governorates ||--o{ pharmacies : has
    governorates ||--o{ delegations : has

    pharmacies ||--o{ stock_levels : records
    medications ||--o{ stock_levels : of
    pharmacies ||--o{ sales_daily : records
    medications ||--o{ sales_daily : of
    pharmacies ||--o{ orders : places
    orders ||--o{ order_items : contains
    medications ||--o{ order_items : of
    pharmacies ||--o{ reservations : holds
    pharmacies ||--o{ returns : logs

    medications ||--o{ national_stock : tracked
    suppliers ||--o{ import_orders : fulfils
    medications ||--o{ import_orders : of
    import_orders ||--o{ shipments : ships
    medications ||--o{ distribution_records : distributed
    governorates ||--o{ distribution_records : to
    medications ||--o{ shortages_history : had

    medications ||--o{ forecasts : predicts
    governorates ||--o{ forecasts : for
    model_runs ||--o{ forecasts : produced
    medications ||--o{ shortage_predictions : predicts
    governorates ||--o{ shortage_predictions : for
    shortage_predictions ||--|| prediction_explanations : explains
    shortage_predictions ||--o{ recommendations : drives
    medications ||--o{ recommendations : about

    medications ||--o{ substitutions : source
    medications ||--o{ substitutions : target

    users }o--o| pharmacies : "works at"
    users }o--o| governorates : oversees
    users }o--o| suppliers : represents

    alerts ||--o{ notifications : fans-out
    users ||--o{ notifications : receives
    users ||--o{ audit_logs : acts

    medications {
        uuid id PK
        string atc_code
        string dci
        string brand_name
        string form
        string dosage
        numeric ddd_value
        numeric unit_price_tnd
        bool is_essential
        bool requires_prescription
    }
    governorates {
        uuid id PK
        string code
        string name_fr
        string name_ar
        int population
        geometry geometry "MultiPolygon 4326"
    }
    pharmacies {
        uuid id PK
        string name
        enum type "community|hospital"
        uuid governorate_id FK
        geometry location "Point 4326"
    }
    sales_daily {
        uuid id PK
        uuid pharmacy_id FK
        uuid medication_id FK
        date date
        int quantity
        bool stockout
    }
    shortage_predictions {
        uuid id PK
        uuid medication_id FK
        uuid governorate_id FK "null = national"
        numeric probability
        enum severity "green..critical"
        date estimated_shortage_date
        numeric coverage_days
    }
    prediction_explanations {
        uuid id PK
        uuid shortage_prediction_id FK
        jsonb shap_values
        jsonb top_factors
        text narrative_fr
        text narrative_ar
    }
    recommendations {
        uuid id PK
        uuid medication_id FK
        enum rec_type
        numeric confidence
        numeric financial_impact_tnd
        numeric expected_shortage_reduction_pct
        enum status "proposed|validated|rejected"
    }
    substitutions {
        uuid id PK
        uuid source_medication_id FK
        uuid target_medication_id FK
        int atc_match_level
        enum equivalence
        numeric ddd_ratio
        bool requires_pharmacist_validation
    }
    audit_logs {
        uuid id PK
        string user_sub
        string action
        string resource
        int status_code
        timestamptz at
    }
```

## Notable constraints & indexes
- `sales_daily`: unique `(pharmacy, medication, date)`; indexes on
  `(medication, date)` and `(pharmacy, date)`.
- `stock_levels`: unique `(pharmacy, medication, recorded_at)`.
- `shortage_predictions`: indexes on `(severity, computed_at)`,
  `(governorate)`, `(medication)`.
- `shipments.delay_days`: generated column `(actual_date - promised_date)`.
- `substitutions`: unique `(source, target)` pair.
- `medications`: GIN trigram indexes on `dci` and `brand_name` for fast search.
- `pharmacies.location`: GiST spatial index for `ST_DWithin` nearest search.
- `audit_logs`: append-only; the application performs no update/delete.

> `atc_code` on `medications` is a full WHO ATC level-5 code (not FK-constrained);
> `atc_classes` holds curated FR/AR labels for the ATC levels the UI displays.
