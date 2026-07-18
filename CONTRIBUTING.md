# Contributing to SentinelleRx

Welcome. This guide gets you from a fresh clone to a running platform with real
data, and explains the few things about this repo that are not obvious.

---

## First run (Windows, no Docker) — the fast path

**Prerequisites**, both must be on your `PATH`:

| Tool | Version | Check |
|---|---|---|
| Python | 3.12+ | `python --version` |
| Node.js | 20+ | `node --version` |

Then:

```bat
git clone https://github.com/Ahmed-Yassine-10/Nabbahni.git
cd Nabbahni
run.bat
```

`run.bat` detects that nothing is set up yet, runs `setup.bat` for you, then
launches both services and opens the browser.

### What the first run actually does, and how long it takes

Nothing is pre-baked in the repo — no database, no trained models. The first
run builds all of it locally, which is why it is slow exactly once:

| Step | Time | What it does |
|---|---|---|
| 1. Virtual environment | ~10 s | Creates `venv` in the runtime folder |
| 2. Python packages | 2–4 min | Installs `requirements-local.txt` |
| 3. Database schema | ~5 s | `create_all()` against SQLite |
| 4. Seed synthetic data | ~1 min | 68 medications, 24 governorates, ~880k sales rows |
| 5. **Train models** | **10–20 min** | XGBoost + LightGBM per horizon, shortage classifier |
| 6. Score predictions | ~1 min | Forecasts, risk levels, SHAP explanations, recommendations |
| 7. Frontend install + build | 3–5 min | `npm install` then `next build` |

**Total: roughly 20–30 minutes.** Step 5 is the long one and it prints little
while it works — that is expected, not a hang. Every later `run.bat` skips
steps 1–5 and starts in under a minute.

### Signing in

There is no registration. Pick a profile from the **role dropdown** (top right);
each one opens a different portal:

| Role | Lands on | What it can see |
|---|---|---|
| Admin PCT | `/cc` | Everything, including model governance |
| Autorité régionale | `/cc` | National view minus models & supply chain |
| Pharmacien (officine / hôpital) | `/pharmacy` | Own stock, suggested orders, substitutions |
| Fournisseur | `/cc/supply-chain` | Delivery commitments |
| Citoyen | `/` | Public search — no login required |

These call `POST /auth/dev-login`, which the API **refuses** whenever Keycloak
is enabled. It is a local-development affordance, not an auth bypass.

---

## Where things live

Runtime state is deliberately **outside the repository**, in
`%LOCALAPPDATA%\SentinelleRx`:

```
%LOCALAPPDATA%\SentinelleRx\
├── venv\              Python virtual environment
├── frontend\          synced copy of frontend/ + node_modules + .next
├── sentinellerx.db    SQLite database
└── .seeded            marker: "data has been generated"
```

Two reasons: this project is often checked out inside OneDrive, whose file
sync corrupts `node_modules` (npm reports success, then sync dehydrates the
files); and it keeps generated state out of `git status`.

**To start completely fresh**, delete that folder and re-run `run.bat`.

Working on two checkouts at once? Point them at separate runtimes:

```bat
set "SENTINELLE_RUNTIME=%LOCALAPPDATA%\SentinelleRx-myfork"
run.bat
```

---

## Everyday commands

| Script | Use it when |
|---|---|
| `run.bat` | Normal start. Stops old servers, syncs, rebuilds, launches. |
| `setup.bat` | Re-run setup only (safe: skips seed/training if already done). |
| `stop.bat` | Stop both services. Also kills whatever holds ports 3000/8000. |

To regenerate data or models after changing the generator or ML code:

```bat
rem from the repo root, with the venv's python
%LOCALAPPDATA%\SentinelleRx\venv\Scripts\python.exe -m generator.seed --seed 42   :: in data-generator\
%LOCALAPPDATA%\SentinelleRx\venv\Scripts\python.exe -m ml.train_all               :: in ml\
%LOCALAPPDATA%\SentinelleRx\venv\Scripts\python.exe -m ml.score                   :: in ml\
```

`ml.train_all` skips retraining only if `ml/artifacts/shortage.joblib` exists —
delete `ml/artifacts/` to force a full retrain.

---

## Gotchas that will cost you an hour

These are real failures that happened during development, not hypotheticals.

**Never run `next dev` and `next build` against the same checkout at once.**
They share the `.next` directory and overwrite each other's compiled chunks.
The symptom is not an error — every `/_next/static/*.js` returns HTTP 400 and
the page renders blank with no data. `run.bat` builds while nothing is serving
for exactly this reason; `web.bat` serves the production build and never uses
`next dev`.

**Batch files must stay CRLF.** `.gitattributes` pins `*.bat` to `eol=crlf`, so
a normal clone is fine. If you edit them with a tool that rewrites line endings,
`cmd.exe` will misparse them in ways that look nothing like a line-ending
problem — it has been observed reading `timeout` as an interactive prompt and
executing fragments of other lines.

**The `Severity` enum inherits `str`.** Comparison operators are defined
explicitly in `backend/app/core/enums.py` because `"critical" < "orange"` is
`True` alphabetically. Do not remove them — the original bug silently discarded
every critical alert.

**Sales are recorded per governorate, not per pharmacy.** Only 24 of the ~78
pharmacies carry sales rows. Anything computing a per-pharmacy rate must
apportion regional demand (see `_attach_coverage` in
`backend/app/api/v1/stock.py`); dividing a pharmacy's stock by regional demand
makes every shelf read "2 days of cover".

---

## Before opening a pull request

Use the project's virtualenv python, **not** whatever `pytest` is on your PATH
— that would be your system interpreter, without the project's dependencies:

```bat
set "PY=%LOCALAPPDATA%\SentinelleRx\venv\Scripts\python.exe"

cd backend  && %PY% -m pytest       :: 11 tests
cd ml       && %PY% -m pytest       :: 4 tests
cd frontend && npx tsc --noEmit     :: type check
cd frontend && npm run build        :: must be warning-free
```

The backend tests are self-contained: `tests/conftest.py` redirects the
database to a throwaway SQLite file before importing the app and creates the
schema itself, so they never touch your dev database and need no environment
setup.

CI runs the same checks (`.github/workflows/`), plus `ruff`, `trivy`,
`pip-audit` and `npm audit`.

### House rules

- **Explainability is not optional.** Any new prediction surface must be able
  to say *why*. Explanations are computed during scoring and stored — never in
  the request path.
- **Recommendations are decision-support.** A pharmacist or PCT officer
  validates the final action. Nothing auto-executes.
- **The severity ramp is reserved.** Green→dark-red encodes shortage severity
  and nothing else, always paired with a text label — never colour alone.
- **French is the primary language**, Arabic is a first-class second with RTL.
  New UI copy should go through `next-intl` (`frontend/messages/*.json`) rather
  than being hardcoded.

---

## Full stack with Docker

The SQLite path above is for convenience. The production target is PostgreSQL +
PostGIS with Keycloak, Redis, RabbitMQ, MinIO, Qdrant, MLflow and the
Prometheus/Grafana stack. See the Docker Compose section of [README.md](README.md).

---

## Known gaps

Honest list of what is not finished, so you do not rediscover it:

- **New UI pages are French-only.** The Arabic locale flips layout correctly
  (RTL verified) but the copy on the newer screens is hardcoded French rather
  than going through `next-intl`. Needs ~80 keys and a native-speaker review.
- **Governorate boundaries are approximate.** They are a Voronoi tessellation
  of the 24 centroids clipped to the *convex hull* of a simplified national
  outline, so the north coast is a straight cut and Cap Bon is missing.
  Dropping in official boundary GeoJSON requires no schema change.
- **Prophet is skipped** unless installed; the boosted models are the champions
  at every horizon regardless.
- **Qdrant semantic substitution** is stubbed — substitution is ATC/DDD based.
- **External data connectors** (WHO alerts, weather, epidemiological feeds) are
  synthetic in the generator; no live integrations exist yet.
