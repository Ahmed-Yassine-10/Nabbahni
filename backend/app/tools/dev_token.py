"""Mint a local development JWT (HS256) for testing when Keycloak is disabled.

Usage:
    python -m app.tools.dev_token --role pct_admin --sub demo-admin

Only valid when KEYCLOAK_ENABLED=false. Never use in production.
"""
from __future__ import annotations

import argparse
import time

from jose import jwt

from app.core.config import settings


def mint(sub: str, roles: list[str], email: str | None = None, hours: int = 12) -> str:
    now = int(time.time())
    claims = {
        "sub": sub,
        "email": email or f"{sub}@dev.local",
        "roles": roles,
        "realm_access": {"roles": roles},
        "iat": now,
        "exp": now + hours * 3600,
    }
    return jwt.encode(claims, settings.secret_key, algorithm="HS256")


def main() -> None:
    parser = argparse.ArgumentParser(description="Mint a dev JWT")
    parser.add_argument("--sub", default="demo-user")
    parser.add_argument("--role", action="append", dest="roles", default=[])
    parser.add_argument("--email", default=None)
    args = parser.parse_args()
    roles = args.roles or ["pct_admin"]
    print(mint(args.sub, roles, args.email))


if __name__ == "__main__":
    main()
