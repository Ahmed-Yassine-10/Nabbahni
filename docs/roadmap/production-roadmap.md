# Production Roadmap (Months 3–12)

Goal: national rollout across all 24 governorates, real integrations, and the
reliability/compliance posture for a healthcare system of national importance.

## Q1 (Months 3–4) — Scale the pilot
- Expand to Grand Tunis + Sfax + Sousse (≈ 40% of national volume).
- Real ETL connectors: PCT ERP, pharmacy POS vendors, supplier EDI.
- Feature store (Feast) for low-latency, consistent features.
- MLflow model registry with staged promotion + automated WAPE gate.

## Q2 (Months 5–7) — National data hub
- All 24 governorates onboarded; partitioned time-series tables live.
- External connectors: INM weather, ONMNE epidemiology, WHO alerts, port/logistics.
- Drift detection automated (PSI + rolling WAPE) → retraining triggers.
- Qdrant-powered semantic substitution search alongside ATC rules.

## Q3 (Months 8–10) — Reliability & reach
- Multi-AZ HA for stateful services; PITR + tested restore drills.
- Native mobile apps (citizen) / PWA hardening; push + SMS notifications.
- Advanced analytics: supplier reliability scoring, scenario simulation.
- SOC2-style controls; full audit + access review cadence.

## Q4 (Months 11–12) — National operations
- Nationwide launch; 24/7 on-call + runbooks.
- Ministry reporting dashboards; open data (aggregate availability) API.
- Continuous model improvement loop with clinician feedback.
- Post-launch DPIA finalized; independent security audit.

## Cross-cutting non-functionals
| Dimension | Target |
|---|---|
| Availability | 99.9% (API) |
| API latency | p95 < 300 ms (cached), < 800 ms (uncached) |
| Throughput | millions of transactions/day (partitioned + HPA) |
| RPO / RTO | ≤ 15 min / ≤ 1 h |
| Explainability | 100% of predictions carry a stored rationale |
