# API Reference

The full OpenAPI 3.1 specification is served live by FastAPI:

- **Interactive docs**: http://localhost:8000/docs (Swagger UI)
- **ReDoc**: http://localhost:8000/redoc
- **Raw spec**: http://localhost:8000/openapi.json
- **Exported snapshot**: `docs/api/openapi.json` (run `make openapi`)

## Conventions
- Base path: `/api/v1`.
- Auth: `Authorization: Bearer <token>` (Keycloak RS256, or dev HS256 token when
  `KEYCLOAK_ENABLED=false`). Public endpoints need no token.
- Pagination: `?page=&page_size=` → `{ items, total, page, page_size }`.
- Errors: `{ "detail": "message" }` with the appropriate HTTP status.
- All timestamps ISO-8601 (UTC); money in TND.

## Endpoint groups
See the [RBAC matrix](../security/rbac-matrix.md) for per-role access.

| Group | Prefix | Purpose |
|---|---|---|
| auth | `/api/v1/me`, `/auth/dev-login` | Identity + dev login |
| medications | `/api/v1/medications` | Catalogue + substitutions (public search) |
| stock | `/api/v1/stock` | Pharmacy + national inventory, ingestion |
| sales | `/api/v1/sales` | Sales ingestion + series |
| forecasts | `/api/v1/forecasts` | Demand forecasts |
| shortages | `/api/v1/shortages` | Predictions, explanation, national map (GeoJSON) |
| recommendations | `/api/v1/recommendations` | List + validate/reject |
| alerts | `/api/v1/alerts` | Role-scoped feed + acknowledge |
| pharmacies | `/api/v1/pharmacies` | Nearby (PostGIS) + detail |
| citizen | `/api/v1/citizen/availability` | Public availability search |
| admin | `/api/v1/admin` | Scoring trigger, model runs, audit logs |

## Example — citizen availability (public)
```bash
curl "http://localhost:8000/api/v1/citizen/availability?q=Amoxicilline"
```

## Example — dev login + protected call
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/dev-login \
  -H 'Content-Type: application/json' \
  -d '{"role":"pct_admin"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/shortages?severity=critical"
```
