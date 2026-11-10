"""Booking flow routes."""
import logging
from datetime import date

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash,
)
from models.booking_model import create_booking, get_booking_by_id, get_passengers
from models.schedule_model import get_route_by_id, get_schedules_for_route
from services.notification_service import notify_booking_confirmed
from models.user_model import get_user_by_id
from routes.user_routes import login_required

booking_bp = Blueprint("booking", __name__)
logger = logging.getLogger(__name__)

BOOKING_SESSION_KEY = "pending_booking"


@booking_bp.route("/book/<int:route_id>", methods=["GET", "POST"])
@login_required
def book(route_id: int):
    route = get_route_by_id(route_id)
    if not route:
        flash("Route not found.", "danger")
        return redirect(url_for("transport.search"))

    travel_date_str = request.args.get("date", str(date.today()))
    try:
        travel_date = date.fromisoformat(travel_date_str)
    except ValueError:
        travel_date = date.today()

    schedules = get_schedules_for_route(route_id, travel_date)

    if request.method == "POST":
        schedule_id     = request.form.get("schedule_id")
        origin_stop     = request.form.get("origin_stop", "").strip()
        destination_stop = request.form.get("destination_stop", "").strip()
        passenger_count = int(request.form.get("passenger_count", 1))

        if not origin_stop or not destination_stop:
            flash("Please provide both origin and destination stops.", "danger")
            return render_template("booking.html", route=route, schedules=schedules,
                                   travel_date=travel_date_str)

        # Store in session to pass to passenger details step
        session[BOOKING_SESSION_KEY] = {
            "route_id":         route_id,
            "schedule_id":      int(schedule_id) if schedule_id else None,
            "journey_date":     travel_date_str,
            "origin_stop":      origin_stop,
            "destination_stop": destination_stop,
            "passenger_count":  passenger_count,
        }
        return redirect(url_for("booking.passenger_details"))

    return render_template("booking.html", route=route, schedules=schedules,
                           travel_date=travel_date_str)


@booking_bp.route("/book/passengers", methods=["GET", "POST"])
@login_required
def passenger_details():
    pending = session.get(BOOKING_SESSION_KEY)
    if not pending:
        flash("No active booking session. Please start again.", "warning")
        return redirect(url_for("transport.search"))

    route = get_route_by_id(pending["route_id"])
    count = pending["passenger_count"]

    if request.method == "POST":
        passengers = []
        for i in range(1, count + 1):
            passengers.append({
                "name":      request.form.get(f"name_{i}", "").strip(),
                "age":       request.form.get(f"age_{i}"),
                "gender":    request.form.get(f"gender_{i}", "unspecified"),
                "id_type":   request.form.get(f"id_type_{i}", ""),
                "id_number": request.form.get(f"id_number_{i}", ""),
            })

        if not all(p["name"] for p in passengers):
            flash("Passenger names are required.", "danger")
            return render_template("passenger_details.html", route=route,
                                   count=count, pending=pending)

        session[BOOKING_SESSION_KEY]["passengers"] = passengers
        return redirect(url_for("booking.confirm_booking"))

    return render_template("passenger_details.html", route=route, count=count, pending=pending)


@booking_bp.route("/book/confirm", methods=["GET", "POST"])
@login_required
def confirm_booking():
    pending = session.get(BOOKING_SESSION_KEY)
    if not pending or "passengers" not in pending:
        return redirect(url_for("transport.search"))

    route    = get_route_by_id(pending["route_id"])
    schedule = None
    if pending.get("schedule_id"):
        schedules = get_schedules_for_route(pending["route_id"])
        schedule  = next((s for s in schedules if s["id"] == pending["schedule_id"]), None)

    if request.method == "POST":
        try:
            booking = create_booking(
                user_id=session["user_id"],
                route_id=pending["route_id"],
                schedule_id=pending.get("schedule_id"),
                journey_date=date.fromisoformat(pending["journey_date"]),
                origin_stop=pending["origin_stop"],
                destination_stop=pending["destination_stop"],
                passengers=pending["passengers"],
                booking_channel=_determine_channel(route),
            )
        except Exception as exc:
            logger.exception("Booking creation failed: %s", exc)
            flash("Could not create booking. Please try again.", "danger")
            return redirect(url_for("transport.search"))

        # Send confirmation notification
        user = get_user_by_id(session["user_id"])
        dep_time = str(schedule["departure_time"]) if schedule else ""
        notify_booking_confirmed(booking, user, dep_time)

        session.pop(BOOKING_SESSION_KEY, None)

        # Redirect to official provider if direct booking not supported
        if booking["booking_channel"] == "redirect" and route.get("raw_source_url"):
            flash(
                f"Your journey has been noted (Ref: {booking['booking_reference']}). "
                f"Please complete your booking on the official website.",
                "info",
            )
        else:
            flash(f"Booking confirmed! Reference: {booking['booking_reference']}", "success")

        return redirect(url_for("booking.booking_done", ref=booking["booking_reference"]))

    return render_template("confirm_booking.html", route=route, schedule=schedule,
                           pending=pending)


@booking_bp.route("/book/done")
@login_required
def booking_done():
    ref     = request.args.get("ref", "")
    booking = None
    passengers = []
    if ref:
        from models.booking_model import get_booking_by_reference
        booking    = get_booking_by_reference(ref)
        if booking:
            passengers = get_passengers(booking["id"])
    return render_template("booking_done.html", booking=booking, passengers=passengers)


def _determine_channel(route: dict) -> str:
    """Return 'platform' if direct booking is supported, else 'redirect'."""
    # Currently all providers use redirect to official portals.
    # Change to 'platform' when a direct API integration is established.
    return "redirect"
