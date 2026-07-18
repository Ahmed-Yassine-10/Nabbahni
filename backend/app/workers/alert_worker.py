"""RabbitMQ consumer that fans out alerts into per-user notifications.

Run with:  python -m app.workers.alert_worker
Consumes the alerts.fanout exchange; for each alert, creates in-app
notifications for the users who should see it (PCT admins nationally, regional
authorities for their governorate, pharmacists for their pharmacy).
"""
from __future__ import annotations

import json
import logging
import time

import pika
from sqlalchemy import select

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.enums import Role
from app.models.ops import Notification
from app.models.reference import User

logging.basicConfig(level=settings.log_level)
log = logging.getLogger("alert_worker")


def _target_users(db, alert: dict) -> list[User]:
    """Resolve which users should be notified for a given alert payload."""
    scope = alert.get("scope")
    users = list(db.scalars(select(User).where(User.role == Role.pct_admin)).all())

    if scope == "governorate" and alert.get("governorate_id"):
        users += list(
            db.scalars(
                select(User).where(
                    User.role == Role.regional_authority,
                    User.governorate_id == alert["governorate_id"],
                )
            ).all()
        )
    if scope == "pharmacy" and alert.get("pharmacy_id"):
        users += list(
            db.scalars(select(User).where(User.pharmacy_id == alert["pharmacy_id"])).all()
        )
    return users


def _handle(alert: dict) -> None:
    db = SessionLocal()
    try:
        for user in _target_users(db, alert):
            db.add(
                Notification(
                    user_id=user.id,
                    alert_id=alert.get("id"),
                    title=alert.get("title_fr", "Nouvelle alerte"),
                    body=alert.get("body_fr"),
                )
            )
        db.commit()
        log.info("Fanned out alert %s", alert.get("id"))
    except Exception as exc:
        db.rollback()
        log.exception("Failed to handle alert: %s", exc)
    finally:
        db.close()


def _callback(ch, method, properties, body) -> None:  # noqa: ANN001
    try:
        alert = json.loads(body)
        _handle(alert)
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    while True:
        try:
            conn = pika.BlockingConnection(pika.URLParameters(settings.rabbitmq_url))
            channel = conn.channel()
            channel.exchange_declare(
                exchange=settings.rabbitmq_alerts_exchange,
                exchange_type="fanout",
                durable=True,
            )
            q = channel.queue_declare(queue="alerts.notifications", durable=True)
            channel.queue_bind(exchange=settings.rabbitmq_alerts_exchange, queue=q.method.queue)
            channel.basic_qos(prefetch_count=16)
            channel.basic_consume(queue=q.method.queue, on_message_callback=_callback)
            log.info("Alert worker ready; waiting for messages...")
            channel.start_consuming()
        except Exception as exc:
            log.warning("Broker connection lost (%s); retrying in 5s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
