"""Pytest fixtures — a FastAPI test client with a dev auth token.

The database is redirected to a throwaway SQLite file *before* the app is
imported, because `app.core.database` builds its engine at import time. Two
reasons this matters:

  * the suite is self-contained — previously it only passed if DATABASE_URL
    happened to point at an already-migrated database, so a fresh clone failed
    with "no such table: users";
  * tests never touch a real dev database.
"""
from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

# ── Must run before any `app.*` import ────────────────────────────────────────
_TEST_DIR = Path(tempfile.mkdtemp(prefix="sentinellerx-tests-"))
os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DIR.as_posix()}/test.db"
os.environ["KEYCLOAK_ENABLED"] = "false"
os.environ.setdefault("SECRET_KEY", "test-secret-not-used-outside-tests")
# ──────────────────────────────────────────────────────────────────────────────

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from jose import jwt  # noqa: E402

import app.models  # noqa: E402,F401  (registers every table on Base.metadata)
from app.core.config import settings  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    """Create every table once for the session, on the throwaway database."""
    Base.metadata.create_all(engine)
    yield
    engine.dispose()


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


def _token(role: str) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": f"{role}@test",
            "email": f"{role}@test",
            "roles": [role],
            "realm_access": {"roles": [role]},
            "iat": now,
            "exp": now + 3600,
        },
        settings.secret_key,
        algorithm="HS256",
    )


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token('pct_admin')}"}


@pytest.fixture
def pharmacist_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_token('community_pharmacist')}"}
