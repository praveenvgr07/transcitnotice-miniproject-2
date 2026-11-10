"""
CMRL GTFS scraper.

Chennai Metro Rail Limited (CMRL) provides GTFS (General Transit Feed
Specification) data.  When a public GTFS feed URL is confirmed, set the
GTFS_FEED_URL below and set is_authorized = True.

GTFS is a standardized open format explicitly designed for third-party use.
Verify the CMRL feed licence at:
  https://www.chennaimetrorail.org

Current status: DISABLED pending public feed URL confirmation.
"""
import io
import zipfile
import csv
import logging
from datetime import datetime

from .base_scraper import BaseScraper
from database.db import DBCursor, fetchone, fetchall, execute

logger = logging.getLogger(__name__)


# ── Update this URL when an official CMRL GTFS feed is published ──────────
GTFS_FEED_URL = ""   # e.g. "https://www.chennaimetrorail.org/gtfs/feed.zip"


class CMRLScraper(BaseScraper):
    provider = "CMRL"
    is_authorized = False   # Set True when feed URL is confirmed + licensed

    def collect(self) -> dict:
        if not self.is_authorized or not GTFS_FEED_URL:
            logger.info(
                "[CMRL] Collection DISABLED – GTFS_FEED_URL not set or not authorized."
            )
            return self._result(errors=["Not authorized or feed URL not configured."])

        logger.info("[CMRL] Fetching GTFS feed from %s", GTFS_FEED_URL)
        resp = self._get(GTFS_FEED_URL, delay=2.0)
        if not resp:
            return self._result(errors=["GTFS feed fetch failed."])

        try:
            zf = zipfile.ZipFile(io.BytesIO(resp.content))
        except zipfile.BadZipFile:
            return self._result(errors=["Downloaded file is not a valid ZIP."])

        errors: list[str] = []
        routes_data = self._parse_csv(zf, "routes.txt")
        trips_data  = self._parse_csv(zf, "trips.txt")
        stops_data  = self._parse_csv(zf, "stops.txt")
        times_data  = self._parse_csv(zf, "stop_times.txt")

        if not routes_data:
            return self._result(errors=["routes.txt missing or empty in GTFS feed."])

        source_id = self._get_source_id()
        inserted = updated = fetched = 0

        for row in routes_data:
            fetched += 1
            route_number = row.get("route_short_name", row.get("route_id", ""))
            route_name   = row.get("route_long_name", "")
            if not route_number:
                continue
            existing = fetchone(
                "SELECT id FROM routes WHERE provider='CMRL' AND route_number=%s",
                (route_number,),
            )
            if existing:
                execute(
                    """UPDATE routes SET route_name=%s, updated_at=NOW()
                       WHERE id=%s""",
                    (route_name, existing["id"]),
                )
                updated += 1
            else:
                execute(
                    """INSERT INTO routes
                       (source_id, provider, route_number, route_name,
                        origin, destination, service_type, source_record_id,
                        raw_source_url, fetched_at)
                       VALUES (%s,'CMRL',%s,%s,%s,%s,'Metro',%s,%s,NOW())""",
                    (
                        source_id, route_number, route_name,
                        row.get("route_long_name", "").split(" - ")[0][:180],
                        row.get("route_long_name", "").split(" - ")[-1][:180],
                        row.get("route_id", ""), GTFS_FEED_URL,
                    ),
                )
                inserted += 1

        # Update source last_success_at
        if source_id:
            execute(
                "UPDATE transport_sources SET last_success_at=NOW(), "
                "fetch_status='success' WHERE id=%s",
                (source_id,),
            )

        return self._result(
            fetched=fetched, inserted=inserted, updated=updated, errors=errors
        )

    # ── Helpers ────────────────────────────────────────────────────────────

    def _parse_csv(self, zf: zipfile.ZipFile, filename: str) -> list[dict]:
        if filename not in zf.namelist():
            logger.warning("[CMRL] %s not found in GTFS zip.", filename)
            return []
        with zf.open(filename) as fh:
            reader = csv.DictReader(io.TextIOWrapper(fh, encoding="utf-8-sig"))
            return list(reader)

    def _get_source_id(self) -> int | None:
        row = fetchone(
            "SELECT id FROM transport_sources WHERE provider='CMRL' LIMIT 1"
        )
        return row["id"] if row else None
