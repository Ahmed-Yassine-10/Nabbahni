"""Application configuration, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- Core ----
    environment: str = "development"
    secret_key: str = "change-me"
    log_level: str = "INFO"

    # ---- Database ----
    database_url: str = (
        "postgresql+psycopg://sentinelle:sentinelle_dev_pw@localhost:5432/sentinellerx"
    )
    db_pool_size: int = 10
    db_max_overflow: int = 20

    # ---- Redis ----
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl_seconds: int = 60

    # ---- RabbitMQ ----
    rabbitmq_url: str = "amqp://sentinelle:sentinelle_dev_pw@localhost:5672/"
    rabbitmq_ingest_exchange: str = "ingest.events"
    rabbitmq_alerts_exchange: str = "alerts.fanout"

    # ---- Keycloak ----
    keycloak_url: str = "http://localhost:8081"
    keycloak_realm: str = "sentinellerx"
    keycloak_api_client_id: str = "sentinellerx-api"
    keycloak_web_client_id: str = "sentinellerx-web"
    keycloak_enabled: bool = False

    # ---- Observability ----
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "sentinellerx-api"
    sentry_dsn: str = ""
    prometheus_enabled: bool = True

    # ---- API ----
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000"

    # ---- MLflow ----
    mlflow_tracking_uri: str = "http://localhost:5000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def keycloak_realm_url(self) -> str:
        return f"{self.keycloak_url}/realms/{self.keycloak_realm}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def keycloak_jwks_url(self) -> str:
        return f"{self.keycloak_realm_url}/protocol/openid-connect/certs"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
