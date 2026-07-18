"""Smoke tests for health, auth, and RBAC gating."""
from __future__ import annotations


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_me_requires_auth(client):
    assert client.get("/api/v1/me").status_code == 401


def test_me_with_token(client, admin_headers):
    r = client.get("/api/v1/me", headers=admin_headers)
    assert r.status_code == 200
    body = r.json()
    assert "pct_admin" in body["roles"]


def test_rbac_forbids_wrong_role(client, pharmacist_headers):
    # National stock is restricted to PCT / regional roles.
    r = client.get("/api/v1/stock/national", headers=pharmacist_headers)
    assert r.status_code == 403


def test_dev_login_issues_token(client):
    r = client.post("/api/v1/auth/dev-login", json={"role": "pct_admin"})
    assert r.status_code == 200
    assert r.json()["role"] == "pct_admin"
    assert r.json()["access_token"]


def test_openapi_complete(client):
    spec = client.get("/openapi.json").json()
    paths = spec["paths"]
    for expected in [
        "/api/v1/medications",
        "/api/v1/shortages",
        "/api/v1/shortages/map",
        "/api/v1/citizen/availability",
        "/api/v1/recommendations",
    ]:
        assert expected in paths, f"missing {expected}"
