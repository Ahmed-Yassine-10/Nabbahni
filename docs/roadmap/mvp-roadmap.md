# MVP Roadmap (Weeks 1–12)

Goal: a validated pilot in **one governorate** (Grand Tunis) proving the core
loop — ingest → forecast → predict → explain → recommend — with real pharmacy
data and PCT sign-off.

## Phase 1 — Foundations (Weeks 1–3)
- [x] Monorepo, docker-compose infra, Keycloak realm, CI.
- [x] Database schema + migrations; API skeleton + RBAC + audit.
- [x] Synthetic data generator for development.
- [ ] Onboard 1–2 pilot pharmacies' historical export format → ETL adapters.

## Phase 2 — Intelligence (Weeks 4–6)
- [x] Feature pipeline + demand models (XGB/LGBM/Prophet) + comparison.
- [x] Shortage classifier + SHAP explanations.
- [x] Recommendation rules engine.
- [ ] Calibrate severity thresholds with PCT domain experts.

## Phase 3 — Product (Weeks 7–9)
- [x] Command Center (map, KPIs, risk board, recommendations).
- [x] Pharmacy Portal (stock, orders, substitutions).
- [x] Citizen Portal (search, availability, nearby pharmacies).
- [ ] French copy review; Arabic translation pass by a native speaker.

## Phase 4 — Pilot hardening (Weeks 10–12)
- [ ] Real Keycloak SSO for pilot users; MFA for PCT.
- [ ] Load test at governorate scale; tune caching + indexes.
- [ ] Observability dashboards + alerting live.
- [ ] Security review + DPIA draft.
- [ ] Pilot go-live with 10–20 Grand Tunis pharmacies + PCT users.

## MVP success criteria
- Demand forecast WAPE ≤ 0.35 on pilot medications (30-day horizon).
- Shortage classifier catches ≥ 70% of pilot stockouts ≥ 7 days ahead.
- Every prediction shown with an explanation; PCT validates ≥ 20 recommendations.
- p95 API latency < 300 ms on cached views.
