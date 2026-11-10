"""Admin dashboard routes – role-based access, full management interface."""
import logging
from functools import wraps

from flask import (
    Blueprint, render_template, request, redirect,
    url_for, session, flash, jsonify,
)
from models.user_model import get_all_users, count_users, toggle_user_active
from models.booking_model import get_all_bookings, count_bookings
from models.schedule_model import get_all_sources, set_source_enabled, get_recent_changes
from models.notification_model import (
    get_scraper_logs, get_failed_deliveries,
)
from services.scheduler import get_job_status
from database.db import execute, fetchone, fetchall

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")
logger = logging.getLogger(__name__)


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session or session.get("user_role") != "admin":
            flash("Admin access required.", "danger")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return decorated


# ── Dashboard ──────────────────────────────────────────────────────────────

@admin_bp.route("/")
@admin_required
def dashboard():
    sources    = get_all_sources()
    jobs       = get_job_status()
    changes    = get_recent_changes(10)
    failed_del = get_failed_deliveries(10)

    stats = {
        "total_users":      count_users(),
        "total_bookings":   count_bookings(),
        "active_sources":   sum(1 for s in sources if s["is_enabled"]),
        "total_sources":    len(sources),
        "failed_deliveries": len(failed_del),
    }

    return render_template(
        "admin/dashboard.html",
        stats=stats,
        sources=sources,
        jobs=jobs,
        recent_changes=changes,
        failed_deliveries=failed_del,
    )


# ── Users ──────────────────────────────────────────────────────────────────

@admin_bp.route("/users")
@admin_required
def users():
    page  = max(int(request.args.get("page", 1)), 1)
    limit = 50
    all_users = get_all_users(limit=limit, offset=(page - 1) * limit)
    return render_template("admin/users.html", users=all_users, page=page)


@admin_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@admin_required
def toggle_user(user_id: int):
    user = fetchone("SELECT * FROM users WHERE id=%s", (user_id,))
    if not user:
        flash("User not found.", "danger")
    else:
        new_status = not bool(user["is_active"])
        toggle_user_active(user_id, new_status)
        flash(f"User {'activated' if new_status else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


# ── Sources ────────────────────────────────────────────────────────────────

@admin_bp.route("/sources")
@admin_required
def sources():
    all_sources = get_all_sources()
    return render_template("admin/sources.html", sources=all_sources)


@admin_bp.route("/sources/<int:source_id>/toggle", methods=["POST"])
@admin_required
def toggle_source(source_id: int):
    src = fetchone("SELECT * FROM transport_sources WHERE id=%s", (source_id,))
    if not src:
        flash("Source not found.", "danger")
    elif not src["is_authorized"]:
        flash("Cannot enable a source that has not been authorized.", "warning")
    else:
        new_state = not bool(src["is_enabled"])
        set_source_enabled(source_id, new_state)
        flash(f"Source {'enabled' if new_state else 'disabled'}.", "success")
    return redirect(url_for("admin.sources"))


# ── Scraper logs ───────────────────────────────────────────────────────────

@admin_bp.route("/scraper-logs")
@admin_required
def scraper_logs():
    logs = get_scraper_logs(limit=200)
    return render_template("admin/scraper_logs.html", logs=logs)


# ── Changes ────────────────────────────────────────────────────────────────

@admin_bp.route("/changes")
@admin_required
def changes():
    all_changes = get_recent_changes(100)
    return render_template("admin/changes.html", changes=all_changes)


# ── Announcements ──────────────────────────────────────────────────────────

@admin_bp.route("/announcements")
@admin_required
def announcements():
    anns = fetchall(
        "SELECT * FROM announcements ORDER BY created_at DESC LIMIT 100"
    )
    return render_template("admin/announcements.html", announcements=anns)


@admin_bp.route("/announcements/new", methods=["GET", "POST"])
@admin_required
def new_announcement():
    providers = ["MTC", "TNSTC", "SETC", "CMRL"]
    if request.method == "POST":
        provider = request.form.get("provider", "MTC")
        title    = request.form.get("title", "").strip()
        body     = request.form.get("body", "").strip()
        ann_type = request.form.get("announcement_type", "general")
        severity = request.form.get("severity", "info")
        src_url  = request.form.get("source_url", "").strip()
        verified = int("is_verified" in request.form)

        if not title or not body:
            flash("Title and body are required.", "danger")
            return render_template("admin/new_announcement.html", providers=providers,
                                   form=request.form)

        execute(
            """INSERT INTO announcements
               (provider, title, body, announcement_type, severity,
                source_url, is_verified)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (provider, title, body, ann_type, severity, src_url or None, verified),
        )
        flash("Announcement created.", "success")
        return redirect(url_for("admin.announcements"))

    return render_template("admin/new_announcement.html", providers=providers, form={})


# ── Bookings ───────────────────────────────────────────────────────────────

@admin_bp.route("/bookings")
@admin_required
def bookings():
    all_bookings = get_all_bookings(limit=200)
    return render_template("admin/bookings.html", bookings=all_bookings)


# ── API: run job manually ──────────────────────────────────────────────────

@admin_bp.route("/api/run-collection", methods=["POST"])
@admin_required
def run_collection_now():
    from services.scheduler import _run_data_collection
    try:
        _run_data_collection()
        return jsonify({"ok": True, "message": "Collection job triggered."})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)}), 500
