"""Notification model – in-app notifications and delivery logs."""
from database.db import fetchone, fetchall, execute
import logging

logger = logging.getLogger(__name__)


def create_notification(
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    booking_id: int = None,
    change_id: int = None,
) -> int:
    return execute(
        """INSERT INTO notifications
           (user_id, booking_id, change_id, notification_type, title, message)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (user_id, booking_id, change_id, notification_type, title, message),
    )


def get_user_notifications(user_id: int, limit: int = 30) -> list[dict]:
    return fetchall(
        """SELECT * FROM notifications
           WHERE user_id = %s
           ORDER BY created_at DESC LIMIT %s""",
        (user_id, limit),
    )


def count_unread(user_id: int) -> int:
    row = fetchone(
        "SELECT COUNT(*) AS cnt FROM notifications WHERE user_id=%s AND is_read=0",
        (user_id,),
    )
    return row["cnt"] if row else 0


def mark_read(notification_id: int, user_id: int) -> None:
    execute(
        "UPDATE notifications SET is_read=1 WHERE id=%s AND user_id=%s",
        (notification_id, user_id),
    )


def mark_all_read(user_id: int) -> None:
    execute(
        "UPDATE notifications SET is_read=1 WHERE user_id=%s AND is_read=0",
        (user_id,),
    )


# ── Delivery logs ──────────────────────────────────────────────────────────

def create_delivery_log(
    notification_id: int, channel: str, recipient: str
) -> int:
    return execute(
        """INSERT INTO notification_delivery_logs
           (notification_id, channel, recipient, status)
           VALUES (%s,%s,%s,'queued')""",
        (notification_id, channel, recipient),
    )


def update_delivery_log(
    log_id: int,
    status: str,
    provider_ref: str = None,
    error_message: str = None,
) -> None:
    execute(
        """UPDATE notification_delivery_logs
           SET status=%s, provider_ref=%s, error_message=%s,
               attempt_count = attempt_count + 1,
               last_attempt_at = NOW(),
               delivered_at = IF(%s='delivered', NOW(), delivered_at)
           WHERE id=%s""",
        (status, provider_ref, error_message, status, log_id),
    )


def get_failed_deliveries(limit: int = 50) -> list[dict]:
    return fetchall(
        """SELECT ndl.*, n.title, n.user_id
           FROM notification_delivery_logs ndl
           JOIN notifications n ON n.id = ndl.notification_id
           WHERE ndl.status = 'failed' AND ndl.attempt_count < 3
           ORDER BY ndl.created_at DESC LIMIT %s""",
        (limit,),
    )


# ── Scraper logs ───────────────────────────────────────────────────────────

def create_scraper_log(source_id: int, provider: str, job_name: str) -> int:
    return execute(
        """INSERT INTO scraper_logs (source_id, provider, job_name, status)
           VALUES (%s,%s,%s,'started')""",
        (source_id, provider, job_name),
    )


def finish_scraper_log(
    log_id: int,
    status: str,
    records_fetched: int = 0,
    records_inserted: int = 0,
    records_updated: int = 0,
    changes_detected: int = 0,
    error_message: str = None,
    duration_ms: int = None,
) -> None:
    execute(
        """UPDATE scraper_logs
           SET status=%s, records_fetched=%s, records_inserted=%s,
               records_updated=%s, changes_detected=%s,
               error_message=%s, duration_ms=%s, completed_at=NOW()
           WHERE id=%s""",
        (
            status, records_fetched, records_inserted, records_updated,
            changes_detected, error_message, duration_ms, log_id,
        ),
    )


def get_scraper_logs(limit: int = 100) -> list[dict]:
    return fetchall(
        """SELECT sl.*, ts.source_name
           FROM scraper_logs sl
           LEFT JOIN transport_sources ts ON ts.id = sl.source_id
           ORDER BY sl.started_at DESC LIMIT %s""",
        (limit,),
    )
