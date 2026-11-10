"""User model – database operations for the users table."""
import logging
from datetime import datetime
import bcrypt
from database.db import DBCursor, fetchone, fetchall, execute

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ── CRUD ──────────────────────────────────────────────────────────────────

def create_user(full_name: str, email: str, mobile: str, password: str) -> int:
    """Insert a new user and return their id."""
    pw_hash = hash_password(password)
    user_id = execute(
        """INSERT INTO users (full_name, email, mobile, password_hash)
           VALUES (%s, %s, %s, %s)""",
        (full_name, email.lower().strip(), mobile.strip(), pw_hash),
    )
    # Create default notification preferences
    execute(
        "INSERT IGNORE INTO notification_preferences (user_id) VALUES (%s)",
        (user_id,),
    )
    return user_id


def get_user_by_id(user_id: int) -> dict | None:
    return fetchone("SELECT * FROM users WHERE id = %s", (user_id,))


def get_user_by_email(email: str) -> dict | None:
    return fetchone("SELECT * FROM users WHERE email = %s", (email.lower().strip(),))


def get_user_by_mobile(mobile: str) -> dict | None:
    return fetchone("SELECT * FROM users WHERE mobile = %s", (mobile.strip(),))


def update_last_login(user_id: int) -> None:
    execute("UPDATE users SET last_login = NOW() WHERE id = %s", (user_id,))


def set_email_verified(user_id: int) -> None:
    execute("UPDATE users SET is_email_verified = 1 WHERE id = %s", (user_id,))


def set_mobile_verified(user_id: int) -> None:
    execute("UPDATE users SET is_mobile_verified = 1 WHERE id = %s", (user_id,))


def update_password(user_id: int, new_password: str) -> None:
    pw_hash = hash_password(new_password)
    execute("UPDATE users SET password_hash = %s WHERE id = %s", (pw_hash, user_id))


def update_profile(user_id: int, full_name: str, mobile: str) -> None:
    execute(
        "UPDATE users SET full_name = %s, mobile = %s WHERE id = %s",
        (full_name, mobile, user_id),
    )


def get_all_users(limit: int = 200, offset: int = 0) -> list[dict]:
    return fetchall(
        "SELECT id, full_name, email, mobile, role, is_active, "
        "is_email_verified, is_mobile_verified, created_at, last_login "
        "FROM users ORDER BY created_at DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )


def count_users() -> int:
    row = fetchone("SELECT COUNT(*) AS cnt FROM users")
    return row["cnt"] if row else 0


def toggle_user_active(user_id: int, active: bool) -> None:
    execute("UPDATE users SET is_active = %s WHERE id = %s", (int(active), user_id))


def get_notification_prefs(user_id: int) -> dict | None:
    return fetchone(
        "SELECT * FROM notification_preferences WHERE user_id = %s", (user_id,)
    )


def update_notification_prefs(user_id: int, prefs: dict) -> None:
    execute(
        """UPDATE notification_preferences
           SET email_enabled=%s, sms_enabled=%s,
               booking_alerts=%s, schedule_alerts=%s, promo_alerts=%s
           WHERE user_id=%s""",
        (
            int(prefs.get("email_enabled", 1)),
            int(prefs.get("sms_enabled", 1)),
            int(prefs.get("booking_alerts", 1)),
            int(prefs.get("schedule_alerts", 1)),
            int(prefs.get("promo_alerts", 0)),
            user_id,
        ),
    )
