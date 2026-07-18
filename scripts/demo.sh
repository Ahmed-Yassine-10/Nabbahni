#!/usr/bin/env bash
# End-to-end demo: infra up → migrate → seed → train → score → smoke-check the API.
# Usage:  bash scripts/demo.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "▶ 1/6  Starting infrastructure…"
docker compose up -d
echo "   waiting for Postgres…"
until docker compose exec -T postgres pg_isready -U sentinelle >/dev/null 2>&1; do sleep 2; done

echo "▶ 2/6  Applying migrations…"
( cd backend && alembic upgrade head )

echo "▶ 3/6  Seeding synthetic data…"
( cd data-generator && python -m generator.seed --seed 42 )

echo "▶ 4/6  Training models…"
( cd ml && python -m ml.train_all )

echo "▶ 5/6  Scoring (predictions + recommendations + alerts)…"
( cd ml && python -m ml.score )

echo "▶ 6/6  Smoke-checking the API…"
( cd backend && uvicorn app.main:app --port 8000 & echo $! > /tmp/srx_api.pid )
sleep 5
curl -fsS "http://localhost:8000/healthz" && echo " ✓ health"
curl -fsS "http://localhost:8000/api/v1/citizen/availability?q=Amoxicilline" >/dev/null && echo " ✓ citizen search"
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/dev-login \
  -H 'Content-Type: application/json' -d '{"role":"pct_admin"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
curl -fsS -H "Authorization: Bearer $TOKEN" "http://localhost:8000/api/v1/shortages/map" >/dev/null \
  && echo " ✓ risk map"
kill "$(cat /tmp/srx_api.pid)" 2>/dev/null || true

echo "✅ Demo pipeline complete. Start the UI with:  cd frontend && npm run dev"
