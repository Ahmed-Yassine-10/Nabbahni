# RBAC Matrix

Roles are Keycloak realm roles, enforced server-side via `require_roles()` in
`backend/app/core/security.py`. ✅ = allowed, — = forbidden, 🌐 = public
(no token required).

| Endpoint | pct_admin | regional_authority | hospital_pharmacist | community_pharmacist | supplier | citizen |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `GET /me` | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| `GET /medications*` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 |
| `GET /citizen/availability` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 |
| `GET /pharmacies/nearby` | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 | 🌐 |
| `GET /stock/pharmacy/{id}` | ✅ | ✅ | ✅ (own) | ✅ (own) | — | — |
| `POST /stock/pharmacy/{id}` | ✅ | — | ✅ | ✅ | — | — |
| `GET /stock/national` | ✅ | ✅ | — | — | — | — |
| `POST /sales/ingest` | ✅ | — | ✅ | ✅ | — | — |
| `GET /sales/series` | ✅ | ✅ | — | — | — | — |
| `GET /forecasts` | ✅ | ✅ | ✅ | ✅ | — | — |
| `GET /shortages*` | ✅ | ✅ | ✅ | ✅ | — | — |
| `GET /shortages/map` | ✅ | ✅ | — | — | — | — |
| `GET /recommendations` | ✅ | ✅ | — | — | — | — |
| `POST /recommendations/{id}/validate` | ✅ | ✅ | — | — | — | — |
| `GET /alerts` | ✅ | ✅ (gov) | ✅ (pharmacy) | ✅ (pharmacy) | — | — |
| `POST /alerts/{id}/ack` | ✅ | ✅ | ✅ | ✅ | — | — |
| `POST /admin/scoring/run` | ✅ | — | — | — | — | — |
| `GET /admin/audit-logs` | ✅ | — | — | — | — | — |

## Scoping rules beyond role
- **Regional authority**: alerts and series scoped to their `governorate_id`.
- **Pharmacist**: stock/orders scoped to their linked `pharmacy_id`; alerts to
  their pharmacy + national.
- **MFA**: `pct_admin` and `regional_authority` require OTP (enforced in the
  Keycloak realm authentication flow).
