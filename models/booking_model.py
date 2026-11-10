"""Booking model – database access for bookings and passengers."""
import secrets
import string
from database.db import fetchone, fetchall, execute, DBCursor
import logging

logger = logging.getLogger(__name__)


def _generate_ref(length: int = 12) -> str:
    alphabet = string.ascii_uppercase + string.digits
    return "TN" + "".join(secrets.choice(alphabet) for _ in range(length))


def create_booking(
    user_id: int,
    route_id: int,
    schedule_id: int | None,
    journey_date,
    origin_stop: str,
    destination_stop: str,
    passengers: list[dict],
    total_fare: float | None = None,
    booking_channel: str = "redirect",
) -> dict:
    """Create booking + passengers in one transaction. Returns booking dict."""
    reference = _generate_ref()

    with DBCursor() as cur:
        cur.execute(
            """INSERT INTO bookings
               (user_id, route_id, schedule_id, booking_reference,
                journey_date, origin_stop, destination_stop,
                passenger_count, total_fare, booking_channel)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (
                user_id, route_id, schedule_id, reference,
                journey_date, origin_stop, destination_stop,
                len(passengers), total_fare, booking_channel,
            ),
        )
        booking_id = cur.lastrowid
        for p in passengers:
            cur.execute(
                """INSERT INTO booking_passengers
                   (booking_id, name, age, gender, id_type, id_number)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (
                    booking_id,
                    p.get("name", ""),
                    p.get("age"),
                    p.get("gender", "unspecified"),
                    p.get("id_type"),
                    p.get("id_number"),
                ),
            )

    return get_booking_by_id(booking_id)


def get_booking_by_id(booking_id: int) -> dict | None:
    return fetchone(
        """SELECT b.*, r.route_number, r.route_name, r.provider,
                  r.origin, r.destination
           FROM bookings b
           JOIN routes r ON r.id = b.route_id
           WHERE b.id = %s""",
        (booking_id,),
    )


def get_booking_by_reference(reference: str) -> dict | None:
    return fetchone(
        """SELECT b.*, r.route_number, r.route_name, r.provider
           FROM bookings b
           JOIN routes r ON r.id = b.route_id
           WHERE b.booking_reference = %s""",
        (reference,),
    )


def get_user_bookings(user_id: int, limit: int = 50) -> list[dict]:
    return fetchall(
        """SELECT b.*, r.route_number, r.route_name, r.provider,
                  r.origin, r.destination
           FROM bookings b
           JOIN routes r ON r.id = b.route_id
           WHERE b.user_id = %s
           ORDER BY b.created_at DESC LIMIT %s""",
        (user_id, limit),
    )


def get_passengers(booking_id: int) -> list[dict]:
    return fetchall(
        "SELECT * FROM booking_passengers WHERE booking_id = %s",
        (booking_id,),
    )


def update_booking_status(
    booking_id: int,
    status: str,
    payment_status: str = None,
    payment_ref: str = None,
    provider_booking_ref: str = None,
) -> None:
    fields = ["booking_status = %s"]
    params = [status]
    if payment_status:
        fields.append("payment_status = %s"); params.append(payment_status)
    if payment_ref:
        fields.append("payment_ref = %s"); params.append(payment_ref)
    if provider_booking_ref:
        fields.append("provider_booking_ref = %s"); params.append(provider_booking_ref)
    params.append(booking_id)
    execute(f"UPDATE bookings SET {', '.join(fields)} WHERE id = %s", tuple(params))


def cancel_booking(booking_id: int, reason: str) -> None:
    execute(
        """UPDATE bookings
           SET booking_status='cancelled', cancellation_reason=%s, cancelled_at=NOW()
           WHERE id = %s""",
        (reason, booking_id),
    )


def get_all_bookings(limit: int = 200, offset: int = 0) -> list[dict]:
    return fetchall(
        """SELECT b.*, u.full_name, u.email,
                  r.route_number, r.provider
           FROM bookings b
           JOIN users u ON u.id = b.user_id
           JOIN routes r ON r.id = b.route_id
           ORDER BY b.created_at DESC LIMIT %s OFFSET %s""",
        (limit, offset),
    )


def count_bookings() -> int:
    row = fetchone("SELECT COUNT(*) AS cnt FROM bookings")
    return row["cnt"] if row else 0


def get_upcoming_bookings_for_route(route_id: int) -> list[dict]:
    """Return confirmed bookings on this route with journey_date >= today."""
    return fetchall(
        """SELECT b.*, u.full_name, u.email, u.mobile
           FROM bookings b
           JOIN users u ON u.id = b.user_id
           WHERE b.route_id = %s
             AND b.booking_status = 'confirmed'
             AND b.journey_date >= CURDATE()""",
        (route_id,),
    )
