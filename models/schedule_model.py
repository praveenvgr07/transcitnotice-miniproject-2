"""Schedule and route model – database access layer."""
from database.db import fetchone, fetchall, execute
import logging

logger = logging.getLogger(__name__)


# ── Routes ────────────────────────────────────────────────────────────────

def search_routes(
    provider: str = None,
    origin: str = None,
    destination: str = None,
    route_number: str = None,
    service_type: str = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    conditions = ["r.is_active = 1"]
    params: list = []

    if provider:
        conditions.append("r.provider = %s")
        params.append(provider)
    if origin:
        conditions.append("r.origin LIKE %s")
        params.append(f"%{origin}%")
    if destination:
        conditions.append("r.destination LIKE %s")
        params.append(f"%{destination}%")
    if route_number:
        conditions.append("r.route_number LIKE %s")
        params.append(f"%{route_number}%")
    if service_type:
        conditions.append("r.service_type = %s")
        params.append(service_type)

    where = " AND ".join(conditions)
    sql = f"""
        SELECT r.*,
               ts.source_name, ts.last_success_at, ts.fetch_status
        FROM routes r
        JOIN transport_sources ts ON ts.id = r.source_id
        WHERE {where}
        ORDER BY r.provider, r.route_number
        LIMIT %s OFFSET %s
    """
    params.extend([limit, offset])
    return fetchall(sql, tuple(params))


def get_route_by_id(route_id: int) -> dict | None:
    return fetchone(
        """SELECT r.*, ts.source_name, ts.last_success_at
           FROM routes r
           JOIN transport_sources ts ON ts.id = r.source_id
           WHERE r.id = %s""",
        (route_id,),
    )


def get_schedules_for_route(route_id: int, travel_date=None) -> list[dict]:
    """Return active schedules, optionally filtering by day-of-week."""
    sql = """
        SELECT * FROM schedules
        WHERE route_id = %s AND is_active = 1
        ORDER BY departure_time
    """
    results = fetchall(sql, (route_id,))
    if travel_date:
        dow = str(travel_date.isoweekday())  # Mon=1 … Sun=7
        results = [r for r in results if dow in r["days_of_week"]]
    return results


def get_stops_for_route(route_id: int) -> list[dict]:
    return fetchall(
        "SELECT * FROM stops WHERE route_id = %s ORDER BY stop_sequence",
        (route_id,),
    )


def get_recent_changes(limit: int = 20) -> list[dict]:
    return fetchall(
        """SELECT sch.*, r.route_number, r.provider, r.origin, r.destination
           FROM schedule_change_history sch
           JOIN routes r ON r.id = sch.route_id
           ORDER BY sch.detected_at DESC
           LIMIT %s""",
        (limit,),
    )


def get_all_sources() -> list[dict]:
    return fetchall(
        "SELECT * FROM transport_sources ORDER BY provider",
        (),
    )


def get_source_by_id(source_id: int) -> dict | None:
    return fetchone("SELECT * FROM transport_sources WHERE id = %s", (source_id,))


def set_source_enabled(source_id: int, enabled: bool) -> None:
    execute(
        "UPDATE transport_sources SET is_enabled = %s WHERE id = %s",
        (int(enabled), source_id),
    )


def get_latest_announcements(limit: int = 10, provider: str = None) -> list[dict]:
    if provider:
        return fetchall(
            """SELECT * FROM announcements
               WHERE provider = %s
               ORDER BY created_at DESC LIMIT %s""",
            (provider, limit),
        )
    return fetchall(
        "SELECT * FROM announcements ORDER BY created_at DESC LIMIT %s",
        (limit,),
    )
