"""Transport search and service detail routes."""
import logging
from datetime import date

from flask import (
    Blueprint, render_template, request, jsonify, session
)
from models.schedule_model import (
    search_routes, get_route_by_id, get_schedules_for_route,
    get_stops_for_route, get_recent_changes, get_all_sources,
    get_latest_announcements,
)
from database.db import fetchall

transport_bp = Blueprint("transport", __name__)
logger = logging.getLogger(__name__)

PROVIDERS = ["MTC", "TNSTC", "SETC", "CMRL"]


@transport_bp.route("/search")
def search():
    provider     = request.args.get("provider", "").strip()
    origin       = request.args.get("origin", "").strip()
    destination  = request.args.get("destination", "").strip()
    route_number = request.args.get("route_number", "").strip()
    travel_date  = request.args.get("travel_date", "").strip()
    service_type = request.args.get("service_type", "").strip()

    results = []
    searched = any([provider, origin, destination, route_number])

    if searched:
        results = search_routes(
            provider=provider or None,
            origin=origin or None,
            destination=destination or None,
            route_number=route_number or None,
            service_type=service_type or None,
            limit=60,
        )

    return render_template(
        "search.html",
        results=results,
        providers=PROVIDERS,
        form=request.args,
        searched=searched,
        travel_date=travel_date,
    )


@transport_bp.route("/service/<int:route_id>")
def service_details(route_id: int):
    route = get_route_by_id(route_id)
    if not route:
        return render_template("404.html"), 404

    travel_date_str = request.args.get("date", "")
    travel_date = None
    if travel_date_str:
        try:
            travel_date = date.fromisoformat(travel_date_str)
        except ValueError:
            pass

    schedules    = get_schedules_for_route(route_id, travel_date)
    stops        = get_stops_for_route(route_id)
    changes      = get_recent_changes(20)
    route_changes = [c for c in changes if c["route_id"] == route_id]

    return render_template(
        "service_details.html",
        route=route,
        schedules=schedules,
        stops=stops,
        changes=route_changes,
        travel_date=travel_date_str,
    )


# ── API endpoints for real-time polling ────────────────────────────────────

@transport_bp.route("/api/announcements")
def api_announcements():
    provider = request.args.get("provider")
    limit    = min(int(request.args.get("limit", 10)), 50)
    data     = get_latest_announcements(limit=limit, provider=provider or None)
    return jsonify({"announcements": _serialize(data)})


@transport_bp.route("/api/changes")
def api_changes():
    data = get_recent_changes(limit=15)
    return jsonify({"changes": _serialize(data)})


@transport_bp.route("/api/sources")
def api_sources():
    sources = get_all_sources()
    result = []
    for s in sources:
        result.append({
            "id":            s["id"],
            "provider":      s["provider"],
            "source_name":   s["source_name"],
            "fetch_status":  s["fetch_status"],
            "last_success":  str(s["last_success_at"]) if s["last_success_at"] else None,
        })
    return jsonify({"sources": result})


# ── SSE endpoint ───────────────────────────────────────────────────────────

@transport_bp.route("/api/sse/updates")
def sse_updates():
    """Server-Sent Events stream for real-time frontend updates."""
    import time
    from flask import Response

    def generate():
        last_change_id = 0
        while True:
            rows = fetchall(
                """SELECT sch.id, sch.change_type, sch.old_value, sch.new_value,
                          sch.detected_at, r.route_number, r.provider
                   FROM schedule_change_history sch
                   JOIN routes r ON r.id = sch.route_id
                   WHERE sch.id > %s
                   ORDER BY sch.id DESC LIMIT 5""",
                (last_change_id,),
            )
            if rows:
                last_change_id = max(r["id"] for r in rows)
                import json
                payload = json.dumps(_serialize(rows))
                yield f"data: {payload}\n\n"
            else:
                yield ": heartbeat\n\n"
            time.sleep(30)   # poll source DB every 30 s

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


def _serialize(rows: list) -> list:
    import datetime
    out = []
    for r in rows:
        d = {}
        for k, v in r.items():
            if isinstance(v, (datetime.datetime, datetime.date)):
                d[k] = str(v)
            elif isinstance(v, datetime.timedelta):
                total = int(v.total_seconds())
                d[k] = f"{total // 3600:02d}:{(total % 3600) // 60:02d}"
            else:
                d[k] = v
        out.append(d)
    return out
