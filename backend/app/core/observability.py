"""Observability wiring: Prometheus metrics, OpenTelemetry tracing, Sentry."""
from __future__ import annotations

import logging

from fastapi import FastAPI

from app.core.config import settings

log = logging.getLogger(__name__)


def setup_observability(app: FastAPI) -> None:
    _setup_sentry()
    _setup_prometheus(app)
    _setup_tracing(app)


def _setup_sentry() -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,
        )
        log.info("Sentry initialised")
    except Exception as exc:  # pragma: no cover
        log.warning("Sentry init failed: %s", exc)


def _setup_prometheus(app: FastAPI) -> None:
    if not settings.prometheus_enabled:
        return
    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        Instrumentator(
            should_group_status_codes=False,
            excluded_handlers=["/metrics", "/healthz", "/readyz"],
        ).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
        log.info("Prometheus metrics exposed at /metrics")
    except Exception as exc:  # pragma: no cover
        log.warning("Prometheus init failed: %s", exc)


def _setup_tracing(app: FastAPI) -> None:
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.otel_service_name})
        provider = TracerProvider(resource=resource)
        provider.add_span_processor(
            BatchSpanProcessor(
                OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
            )
        )
        trace.set_tracer_provider(provider)
        FastAPIInstrumentor.instrument_app(app)
        log.info("OpenTelemetry tracing enabled")
    except Exception as exc:  # pragma: no cover - tracing optional in dev
        log.warning("OpenTelemetry init skipped: %s", exc)
