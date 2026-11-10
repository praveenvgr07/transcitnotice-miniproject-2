import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Flask ──────────────────────────────────────────────────────────────
    SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_PERMANENT = False

    # ── Database ───────────────────────────────────────────────────────────
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_NAME = os.environ.get("DB_NAME", "transitnotice")
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_CHARSET = "utf8mb4"

    # ── Email ──────────────────────────────────────────────────────────────
    MAIL_PROVIDER = os.environ.get("MAIL_PROVIDER", "smtp")   # smtp | sendgrid
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "noreply@transitnotice.in")
    SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY", "")

    # ── SMS ────────────────────────────────────────────────────────────────
    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "twilio")   # twilio | msg91
    TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER", "")
    MSG91_API_KEY = os.environ.get("MSG91_API_KEY", "")
    MSG91_SENDER_ID = os.environ.get("MSG91_SENDER_ID", "TRNTNC")
    MSG91_TEMPLATE_ID = os.environ.get("MSG91_TEMPLATE_ID", "")

    # ── App ────────────────────────────────────────────────────────────────
    APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:5000")
    TIMEZONE = os.environ.get("TIMEZONE", "Asia/Kolkata")

    # ── Scheduler ──────────────────────────────────────────────────────────
    SCHEDULER_INTERVAL_MINUTES = int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", 10))
    SCHEDULER_ENABLED = os.environ.get("SCHEDULER_ENABLED", "true").lower() == "true"

    # ── Token expiry ───────────────────────────────────────────────────────
    EMAIL_VERIFY_EXPIRY = int(os.environ.get("EMAIL_VERIFY_EXPIRY", 86400))
    OTP_EXPIRY = int(os.environ.get("OTP_EXPIRY", 300))
    PASSWORD_RESET_EXPIRY = int(os.environ.get("PASSWORD_RESET_EXPIRY", 3600))


class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_ENV = "development"


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    cls = config_map.get(env, DevelopmentConfig)
    return cls()
