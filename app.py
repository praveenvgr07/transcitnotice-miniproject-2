"""
TransitNotice – Flask Application Entry Point
"""
import atexit
import logging
import os

from flask import Flask
from dotenv import load_dotenv

load_dotenv()

from config import get_config
from database.db import init_pool
from routes.main_routes import main_bp
from routes.auth_routes import auth_bp
from routes.user_routes import user_bp
from routes.transport_routes import transport_bp
from routes.booking_routes import booking_bp
from routes.admin_routes import admin_bp

# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")

    cfg = get_config()
    app.secret_key     = cfg.SECRET_KEY
    app.config_obj     = cfg          # Attach for use in routes/services

    # ── Database pool ──────────────────────────────────────────────────────
    # Soft-fail: app starts in degraded mode if MySQL is not yet configured.
    # Configure .env with DB_PASSWORD (and run init_db.py) to enable full features.
    try:
        init_pool(cfg)
        app.config["DB_READY"] = True
    except Exception as exc:
        logger.critical(
            "Database initialisation failed – running in degraded mode. "
            "Set DB_PASSWORD in .env and run: python database/init_db.py\n%s", exc
        )
        app.config["DB_READY"] = False

    # ── Blueprints ─────────────────────────────────────────────────────────
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(transport_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(admin_bp)

    # ── Template globals ───────────────────────────────────────────────────
    @app.context_processor
    def inject_globals():
        from flask import session
        from models.notification_model import count_unread
        unread = 0
        if "user_id" in session:
            try:
                unread = count_unread(session["user_id"])
            except Exception:
                pass
        return {
            "app_name": "TransitNotice",
            "unread_count": unread,
        }

    # ── Background scheduler ───────────────────────────────────────────────
    if app.config.get("DB_READY") and (
        not app.debug or os.environ.get("WERKZEUG_RUN_MAIN") == "true"
    ):
        from services.scheduler import init_scheduler, shutdown_scheduler
        init_scheduler(cfg)
        atexit.register(shutdown_scheduler)
    elif not app.config.get("DB_READY"):
        logger.warning("Scheduler disabled – database not available.")

    return app


app = create_app()

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    app.run(host="0.0.0.0", port=5000, debug=debug)
