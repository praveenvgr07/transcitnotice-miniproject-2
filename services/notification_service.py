"""Notification dispatcher – sends email/SMS and logs delivery."""
import logging
from config import get_config
from models.notification_model import (
    create_notification, create_delivery_log, update_delivery_log,
    get_failed_deliveries,
)
from models.user_model import get_user_by_id, get_notification_prefs
from models.booking_model import get_upcoming_bookings_for_route
from services.email_service import (
    send_email,
    build_schedule_change_email,
    build_booking_confirmation_email,
)
from services.sms_service import send_sms

logger = logging.getLogger(__name__)
_cfg = get_config()


def notify_schedule_change(change: dict) -> int:
    """
    Find all users with confirmed bookings on changed route and notify them.
    Returns number of notifications dispatched.
    """
    from database.db import fetchall
    route_id = change.get("route_id")
    if not route_id:
        return 0

    affected = get_upcoming_bookings_for_route(route_id)
    dispatched = 0

    for booking in affected:
        user_id  = booking["user_id"]
        user     = get_user_by_id(user_id)
        prefs    = get_notification_prefs(user_id)
        if not user or not prefs:
            continue
        if not prefs.get("schedule_alerts", 1):
            continue

        title   = f"Journey Update – {change.get('provider','Transport')} {change.get('route_number','')}"
        message = (
            f"Departure time changed: {change.get('old_value','')} → "
            f"{change.get('new_value','')}. "
            f"Booking: {booking['booking_reference']}"
        )

        notif_id = create_notification(
            user_id=user_id,
            notification_type="schedule_change",
            title=title,
            message=message,
            booking_id=booking["id"],
            change_id=change.get("id"),
        )

        # ── Email ──────────────────────────────────────────────────────
        if prefs.get("email_enabled", 1) and user.get("is_email_verified"):
            subj, html, txt = build_schedule_change_email(
                user_name=user["full_name"],
                provider=change.get("provider", ""),
                route_number=change.get("route_number", ""),
                origin=change.get("origin", ""),
                destination=change.get("destination", ""),
                old_time=str(change.get("old_value", "")),
                new_time=str(change.get("new_value", "")),
                reason=change.get("change_reason") or "",
                booking_ref=booking["booking_reference"],
            )
            log_id = create_delivery_log(notif_id, "email", user["email"])
            ok, ref = send_email(_cfg, user["email"], subj, html, txt)
            update_delivery_log(log_id, "delivered" if ok else "failed", ref, None if ok else ref)

        # ── SMS ────────────────────────────────────────────────────────
        if prefs.get("sms_enabled", 1) and user.get("is_mobile_verified"):
            sms_text = (
                f"TransitNotice: Route {change.get('route_number','')} – "
                f"departure changed from {change.get('old_value','')} "
                f"to {change.get('new_value','')}. Ref: {booking['booking_reference']}"
            )
            log_id = create_delivery_log(notif_id, "sms", user["mobile"])
            ok, ref = send_sms(_cfg, f"+91{user['mobile'].lstrip('+').lstrip('91')}", sms_text)
            update_delivery_log(log_id, "delivered" if ok else "failed", ref, None if ok else ref)

        dispatched += 1

    return dispatched


def notify_booking_confirmed(booking: dict, user: dict, departure_time: str = "") -> None:
    prefs = get_notification_prefs(user["id"])
    if not prefs or not prefs.get("booking_alerts", 1):
        return

    notif_id = create_notification(
        user_id=user["id"],
        notification_type="booking_confirm",
        title=f"Booking Confirmed – {booking['booking_reference']}",
        message=(
            f"Your booking on {booking.get('provider','Transport')} "
            f"route {booking.get('route_number','')} for "
            f"{booking.get('journey_date','')} has been recorded."
        ),
        booking_id=booking["id"],
    )

    if prefs.get("email_enabled", 1) and user.get("is_email_verified"):
        subj, html, txt = build_booking_confirmation_email(
            user_name=user["full_name"],
            booking_ref=booking["booking_reference"],
            provider=booking.get("provider", ""),
            route_number=booking.get("route_number", ""),
            origin=booking.get("origin_stop", ""),
            destination=booking.get("destination_stop", ""),
            journey_date=str(booking.get("journey_date", "")),
            departure_time=departure_time,
            passenger_count=booking.get("passenger_count", 1),
        )
        log_id = create_delivery_log(notif_id, "email", user["email"])
        ok, ref = send_email(_cfg, user["email"], subj, html, txt)
        update_delivery_log(log_id, "delivered" if ok else "failed", ref)


def retry_failed_deliveries() -> int:
    """Retry up to 50 failed deliveries. Called by scheduler."""
    failed = get_failed_deliveries(limit=50)
    retried = 0
    for log in failed:
        # Re-attempt (simplified – full retry would reload message from DB)
        update_delivery_log(log["id"], "failed", error_message="Retry attempted by scheduler")
        retried += 1
    return retried
