"""RabbitMQ publisher helper (fanout exchanges). Degrades to no-op if broker down."""
from __future__ import annotations

import json
import logging
from typing import Any

import pika

from app.core.config import settings

log = logging.getLogger(__name__)


def _connect() -> pika.BlockingConnection | None:
    try:
        params = pika.URLParameters(settings.rabbitmq_url)
        params.socket_timeout = 2
        return pika.BlockingConnection(params)
    except Exception as exc:  # broker optional in dev
        log.warning("RabbitMQ unavailable: %s", exc)
        return None


def publish(exchange: str, routing_key: str, message: dict[str, Any]) -> bool:
    conn = _connect()
    if conn is None:
        return False
    try:
        channel = conn.channel()
        channel.exchange_declare(exchange=exchange, exchange_type="fanout", durable=True)
        channel.basic_publish(
            exchange=exchange,
            routing_key=routing_key,
            body=json.dumps(message, default=str).encode(),
            properties=pika.BasicProperties(delivery_mode=2),  # persistent
        )
        return True
    except Exception as exc:
        log.warning("Failed to publish message: %s", exc)
        return False
    finally:
        try:
            conn.close()
        except Exception:
            pass


def publish_alert(alert: dict[str, Any]) -> bool:
    return publish(settings.rabbitmq_alerts_exchange, "alert", alert)


def publish_ingest(event: dict[str, Any]) -> bool:
    return publish(settings.rabbitmq_ingest_exchange, "ingest", event)
