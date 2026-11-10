"""Change detection engine – compares new vs existing schedule data."""
import logging
from database.db import fetchone, fetchall, execute

logger = logging.getLogger(__name__)

CHANGE_TYPES = {
    "departure_change",
    "arrival_change",
    "cancellation",
    "diversion",
    "stop_change",
    "new_schedule",
    "service_resumption",
}

# Minimum difference in minutes before flagging a departure time change
MIN_TIME_DELTA_MINUTES = 1


def _time_to_minutes(t) -> int | None:
    """Convert TIME value (timedelta or 'HH:MM:SS' str) to total minutes."""
    if t is None:
        return None
    if hasattr(t, "seconds"):                          # timedelta from MySQL
        return t.seconds // 60
    if isinstance(t, str):
        parts = t.split(":")
        return int(parts[0]) * 60 + int(parts[1])
    return None


def detect_schedule_changes(route_id: int, new_schedules: list[dict]) -> int:
    """
    Compare new_schedules (list of dicts with departure_time, arrival_time,
    trip_number, days_of_week, is_active) against current DB records.

    Returns number of changes detected and recorded.
    """
    existing = fetchall(
        "SELECT * FROM schedules WHERE route_id=%s", (route_id,)
    )
    existing_map = {r["source_record_id"]: r for r in existing if r.get("source_record_id")}

    changes_detected = 0

    for new in new_schedules:
        src_id = new.get("source_record_id") or new.get("trip_number", "")
        old = existing_map.get(src_id)

        if old is None:
            # Brand new schedule
            _record_change(
                route_id=route_id,
                change_type="new_schedule",
                old_value=None,
                new_value=str(new),
                confirmed=True,
            )
            changes_detected += 1
            continue

        # ── Check departure time ─────────────────────────────────────────
        old_dep = _time_to_minutes(old.get("departure_time"))
        new_dep = _time_to_minutes(new.get("departure_time"))
        if old_dep is not None and new_dep is not None:
            if abs(old_dep - new_dep) >= MIN_TIME_DELTA_MINUTES:
                if not _change_already_exists(route_id, old["id"], "departure_change"):
                    _record_change(
                        route_id=route_id,
                        schedule_id=old["id"],
                        change_type="departure_change",
                        old_value=str(old.get("departure_time")),
                        new_value=str(new.get("departure_time")),
                        confirmed=True,
                    )
                    changes_detected += 1

        # ── Check arrival time ───────────────────────────────────────────
        old_arr = _time_to_minutes(old.get("arrival_time"))
        new_arr = _time_to_minutes(new.get("arrival_time"))
        if old_arr is not None and new_arr is not None:
            if abs(old_arr - new_arr) >= MIN_TIME_DELTA_MINUTES:
                if not _change_already_exists(route_id, old["id"], "arrival_change"):
                    _record_change(
                        route_id=route_id,
                        schedule_id=old["id"],
                        change_type="arrival_change",
                        old_value=str(old.get("arrival_time")),
                        new_value=str(new.get("arrival_time")),
                        confirmed=True,
                    )
                    changes_detected += 1

        # ── Check cancellation ───────────────────────────────────────────
        was_active = bool(old.get("is_active", 1))
        now_active = bool(new.get("is_active", 1))
        if was_active and not now_active:
            if not _change_already_exists(route_id, old["id"], "cancellation"):
                _record_change(
                    route_id=route_id,
                    schedule_id=old["id"],
                    change_type="cancellation",
                    old_value="active",
                    new_value="cancelled",
                    confirmed=True,
                )
                changes_detected += 1
        elif not was_active and now_active:
            _record_change(
                route_id=route_id,
                schedule_id=old["id"],
                change_type="service_resumption",
                old_value="cancelled",
                new_value="active",
                confirmed=True,
            )
            changes_detected += 1

    return changes_detected


def _record_change(
    route_id: int,
    change_type: str,
    old_value: str | None,
    new_value: str | None,
    schedule_id: int = None,
    confirmed: bool = False,
    reason: str = None,
) -> int:
    return execute(
        """INSERT INTO schedule_change_history
           (route_id, schedule_id, change_type, old_value, new_value,
            change_reason, is_confirmed)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (route_id, schedule_id, change_type, old_value, new_value, reason, int(confirmed)),
    )


def _change_already_exists(
    route_id: int, schedule_id: int, change_type: str, window_minutes: int = 30
) -> bool:
    """Prevent duplicate change records within a time window."""
    row = fetchone(
        """SELECT id FROM schedule_change_history
           WHERE route_id=%s AND schedule_id=%s AND change_type=%s
             AND detected_at >= NOW() - INTERVAL %s MINUTE
           LIMIT 1""",
        (route_id, schedule_id, change_type, window_minutes),
    )
    return row is not None


def get_recent_changes_for_user(user_id: int, limit: int = 20) -> list[dict]:
    """Return schedule changes relevant to a user's upcoming bookings."""
    return fetchall(
        """SELECT sch.*, r.route_number, r.provider, r.origin, r.destination,
                  b.booking_reference, b.journey_date
           FROM schedule_change_history sch
           JOIN routes r ON r.id = sch.route_id
           JOIN bookings b ON b.route_id = sch.route_id
           WHERE b.user_id = %s
             AND b.booking_status = 'confirmed'
             AND b.journey_date >= CURDATE()
             AND sch.detected_at >= b.created_at
           ORDER BY sch.detected_at DESC
           LIMIT %s""",
        (user_id, limit),
    )
