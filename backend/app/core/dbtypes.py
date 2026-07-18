"""Dialect-portable column types.

Production runs on PostgreSQL (JSONB, native UUID). Local development can run on
SQLite so the platform is demoable without external infrastructure. These helpers
pick the right implementation per dialect at DDL time.
"""
from __future__ import annotations

import uuid

from sqlalchemy import CHAR, JSON
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.types import TypeDecorator


class JSONType(TypeDecorator):
    """JSONB on PostgreSQL, generic JSON elsewhere (SQLite)."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class GUID(TypeDecorator):
    """Platform-independent UUID: native on PostgreSQL, CHAR(36) on SQLite."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PgUUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
