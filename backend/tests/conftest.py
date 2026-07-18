"""Pytest fixtures — a FastAPI test client with a dev auth token."""
from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import app


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
