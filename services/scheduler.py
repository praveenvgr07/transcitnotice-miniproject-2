"""
APScheduler background scheduler – data collection every 10 minutes.

Runs independently of Flask web requests.
Uses Asia/Kolkata timezone.
Prevents overlapping jobs with max_instances=1.
"""
import logging
import time
from datetime import datetime

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

IST = pytz.timezone("Asia/Kolkata")

_scheduler: BackgroundScheduler | None = None


def _run_data_collection():
    """Main job – collect data from all enabled sources."""
    from database.db import fetchall, execute
    from scrapers.mtc_scraper  import MTCScraper
    from scrapers.tnstc_scraper import TNSTCScraper
    from scrapers.setc_scraper  import SETCScraper
    from scrapers.cmrl_scraper  import CMRLScraper
    from models.notification_model import create_scraper_log, finish_scraper_log
    from services.change_detector  import detect_schedule_changes
    from services.notification_service import notify_schedule_change

    logger.info("[Scheduler] Data collection job started at %s",
                datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"))

    scrapers = {
        "MTC":   MTCScraper,
        "TNSTC": TNSTCScraper,
        "SETC":  SETCScraper,
        "CMRL":  CMRLScraper,
    }

    enabled_sources = fetchall(
        "SELECT * FROM transport_sources WHERE is_enabled=1 AND is_authorized=1"
    )

    for source in enabled_sources:
        provider   = source["provider"]
        source_id  = source["id"]
        scraper_cls = scrapers.get(provider)
        if not scraper_cls:
            continue

        log_id = create_scraper_log(source_id, provider, f"{provider}_collect")
        start_ms = time.time()

        # Mark fetch started
        execute(
            "UPDATE transport_sources SET last_fetched_at=NOW(), fetch_status='pending' WHERE id=%s",
            (source_id,),
        )

        try:
            scraper = scraper_cls()
            scraper.source_id = source_id
            result = scraper.collect()

            duration = int((time.time() - start_ms) * 1000)
            status   = "success" if not result["errors"] else "partial"

            finish_scraper_log(
                log_id,
                status=status,
                records_fetched=result["records_fetched"],
                records_inserted=result["records_inserted"],
                records_updated=result["records_updated"],
                changes_detected=result["changes_detected"],
                error_message="; ".join(result["errors"]) or None,
                duration_ms=duration,
            )

            execute(
                "UPDATE transport_sources SET last_success_at=NOW(), fetch_status=%s WHERE id=%s",
                (status, source_id),
            )
            logger.info("[Scheduler] %s: fetched=%d ins=%d upd=%d chg=%d",
                        provider,
                        result["records_fetched"],
                        result["records_inserted"],
                        result["records_updated"],
                        result["changes_detected"])

        except Exception as exc:
            duration = int((time.time() - start_ms) * 1000)
            logger.exception("[Scheduler] %s job crashed: %s", provider, exc)
            finish_scraper_log(log_id, "failed", error_message=str(exc), duration_ms=duration)
            execute(
                "UPDATE transport_sources SET fetch_status='failed' WHERE id=%s",
                (source_id,),
            )


def _run_notification_retry():
    """Retry failed delivery attempts."""
    from services.notification_service import retry_failed_deliveries
    try:
        count = retry_failed_deliveries()
        if count:
            logger.info("[Scheduler] Retried %d failed notifications.", count)
    except Exception as exc:
        logger.error("[Scheduler] Notification retry error: %s", exc)


def init_scheduler(app_config) -> None:
    """Create and start the background scheduler. Call once at app startup."""
    global _scheduler

    if not app_config.SCHEDULER_ENABLED:
        logger.info("Scheduler is DISABLED via SCHEDULER_ENABLED=false.")
        return

    if _scheduler and _scheduler.running:
        logger.warning("Scheduler already running – skipping re-init.")
        return

    jobstores   = {"default": MemoryJobStore()}
    executors   = {"default": ThreadPoolExecutor(max_workers=4)}
    job_defaults = {"coalesce": True, "max_instances": 1, "misfire_grace_time": 60}

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone=IST,
    )

    interval = app_config.SCHEDULER_INTERVAL_MINUTES

    _scheduler.add_job(
        _run_data_collection,
        trigger="interval",
        minutes=interval,
        id="data_collection",
        name=f"Data Collection (every {interval} min)",
        replace_existing=True,
    )

    _scheduler.add_job(
        _run_notification_retry,
        trigger="interval",
        minutes=30,
        id="notification_retry",
        name="Notification Retry (every 30 min)",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler started. Data collection every %d minutes (IST).", interval)


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")


def get_job_status() -> list[dict]:
    """Return current job metadata for admin dashboard."""
    if not _scheduler:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append({
            "id":          job.id,
            "name":        job.name,
            "next_run":    job.next_run_time.strftime("%Y-%m-%d %H:%M:%S IST")
                           if job.next_run_time else "paused",
        })
    return jobs
