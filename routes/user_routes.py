"""User dashboard, profile, saved routes, and notifications."""
import logging
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify,
)
from models.user_model import (
    get_user_by_id, update_profile, update_password,
    get_notification_prefs, update_notification_prefs, verify_password,
)
from models.booking_model import get_user_bookings, get_booking_by_id, cancel_booking
from models.notification_model import (
    get_user_notifications, count_unread, mark_read, mark_all_read,
)
from models.schedule_model import get_latest_announcements
from database.db import fetchall, execute

user_bp = Blueprint("user", __name__)
logger = logging.getLogger(__name__)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("auth.login", next=request.url))
        return f(*args, **kwargs)
    return decorated


@user_bp.route("/dashboard")
@login_required
def dashboard():
    user       = get_user_by_id(session["user_id"])
    bookings   = get_user_bookings(session["user_id"], limit=5)
    notifs     = get_user_notifications(session["user_id"], limit=5)
    unread     = count_unread(session["user_id"])
    saved      = _get_saved_routes(session["user_id"])
    announcements = get_latest_announcements(limit=5)
    return render_template(
        "dashboard.html",
        user=user,
        bookings=bookings,
        notifications=notifs,
        unread_count=unread,
        saved_routes=saved,
        announcements=announcements,
    )


# ── Profile ────────────────────────────────────────────────────────────────

@user_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = get_user_by_id(session["user_id"])
    prefs = get_notification_prefs(session["user_id"])

    if request.method == "POST":
        action = request.form.get("action")

        if action == "update_profile":
            full_name = request.form.get("full_name", "").strip()
            mobile    = request.form.get("mobile", "").strip()
            if len(full_name) >= 2:
                update_profile(session["user_id"], full_name, mobile)
                session["user_name"] = full_name
                flash("Profile updated.", "success")
            else:
                flash("Name must be at least 2 characters.", "danger")

        elif action == "change_password":
            current_pw = request.form.get("current_password", "")
            new_pw     = request.form.get("new_password", "")
            confirm    = request.form.get("confirm_password", "")
            if not verify_password(current_pw, user["password_hash"]):
                flash("Current password is incorrect.", "danger")
            elif len(new_pw) < 8:
                flash("New password must be at least 8 characters.", "danger")
            elif new_pw != confirm:
                flash("New passwords do not match.", "danger")
            else:
                update_password(session["user_id"], new_pw)
                flash("Password changed successfully.", "success")

        elif action == "update_prefs":
            new_prefs = {
                "email_enabled":   int("email_enabled" in request.form),
                "sms_enabled":     int("sms_enabled" in request.form),
                "booking_alerts":  int("booking_alerts" in request.form),
                "schedule_alerts": int("schedule_alerts" in request.form),
                "promo_alerts":    int("promo_alerts" in request.form),
            }
            update_notification_prefs(session["user_id"], new_prefs)
            flash("Notification preferences saved.", "success")

        return redirect(url_for("user.profile"))

    return render_template("profile.html", user=user, prefs=prefs)


# ── Bookings ───────────────────────────────────────────────────────────────

@user_bp.route("/bookings")
@login_required
def booking_history():
    bookings = get_user_bookings(session["user_id"])
    return render_template("booking_history.html", bookings=bookings)


@user_bp.route("/bookings/<int:booking_id>/cancel", methods=["POST"])
@login_required
def cancel_booking_view(booking_id: int):
    booking = get_booking_by_id(booking_id)
    if not booking or booking["user_id"] != session["user_id"]:
        flash("Booking not found.", "danger")
        return redirect(url_for("user.booking_history"))
    reason = request.form.get("reason", "Cancelled by user")
    cancel_booking(booking_id, reason)
    flash("Cancellation request submitted.", "info")
    return redirect(url_for("user.booking_history"))


# ── Notifications ──────────────────────────────────────────────────────────

@user_bp.route("/notifications")
@login_required
def notifications():
    notifs  = get_user_notifications(session["user_id"], limit=50)
    unread  = count_unread(session["user_id"])
    return render_template("notifications.html", notifications=notifs, unread_count=unread)


@user_bp.route("/notifications/<int:notif_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notif_id: int):
    mark_read(notif_id, session["user_id"])
    return jsonify({"ok": True})


@user_bp.route("/notifications/read-all", methods=["POST"])
@login_required
def mark_all_notifications_read():
    mark_all_read(session["user_id"])
    return jsonify({"ok": True})


@user_bp.route("/api/notifications/unread-count")
@login_required
def api_unread_count():
    return jsonify({"count": count_unread(session["user_id"])})


# ── Saved routes ───────────────────────────────────────────────────────────

@user_bp.route("/saved-routes/add", methods=["POST"])
@login_required
def save_route():
    route_id    = request.form.get("route_id")
    origin      = request.form.get("origin", "").strip()
    destination = request.form.get("destination", "").strip()
    label       = request.form.get("label", "").strip()
    provider    = request.form.get("provider", "").strip()

    execute(
        """INSERT IGNORE INTO saved_routes
           (user_id, route_id, label, origin, destination, provider)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (session["user_id"], route_id or None, label or None, origin, destination, provider or None),
    )
    flash("Route saved to your favourites.", "success")
    return redirect(request.referrer or url_for("user.dashboard"))


@user_bp.route("/saved-routes/<int:sr_id>/delete", methods=["POST"])
@login_required
def delete_saved_route(sr_id: int):
    execute(
        "DELETE FROM saved_routes WHERE id=%s AND user_id=%s",
        (sr_id, session["user_id"]),
    )
    flash("Saved route removed.", "info")
    return redirect(url_for("user.dashboard"))


def _get_saved_routes(user_id: int) -> list:
    return fetchall(
        """SELECT sr.*, r.route_number, r.route_name
           FROM saved_routes sr
           LEFT JOIN routes r ON r.id = sr.route_id
           WHERE sr.user_id = %s
           ORDER BY sr.created_at DESC""",
        (user_id,),
    )
