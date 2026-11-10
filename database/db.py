"""Database connection pool and helpers."""
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
import logging
from config import get_config

logger = logging.getLogger(__name__)
_pool: pooling.MySQLConnectionPool | None = None


def init_pool(config=None) -> None:
    """Create the global connection pool. Call once at app startup."""
    global _pool
    cfg = config or get_config()
    try:
        _pool = pooling.MySQLConnectionPool(
            pool_name="transitnotice_pool",
            pool_size=10,
            pool_reset_session=True,
            host=cfg.DB_HOST,
            port=cfg.DB_PORT,
            database=cfg.DB_NAME,
            user=cfg.DB_USER,
            password=cfg.DB_PASSWORD,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            use_pure=True,
            time_zone="+05:30",
            autocommit=False,
        )
        logger.info("MySQL connection pool initialised (size=10).")
    except MySQLError as exc:
        logger.critical("Failed to create MySQL pool: %s", exc)
        raise


def get_connection():
    """Return a pooled connection. Caller must close() it."""
    if _pool is None:
        raise RuntimeError("Database pool not initialised. Call init_pool() first.")
    return _pool.get_connection()


class DBCursor:
    """Context manager: auto-commit on success, rollback on error, returns cursor."""

    def __init__(self, dictionary=True):
        self.dictionary = dictionary
        self._conn = None
        self._cursor = None

    def __enter__(self):
        self._conn = get_connection()
        self._cursor = self._conn.cursor(dictionary=self.dictionary)
        return self._cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self._conn.rollback()
            logger.error("DB transaction rolled back: %s", exc_val)
        else:
            self._conn.commit()
        self._cursor.close()
        self._conn.close()
        return False   # re-raise exceptions


def fetchone(sql: str, params: tuple = ()) -> dict | None:
    with DBCursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def fetchall(sql: str, params: tuple = ()) -> list[dict]:
    with DBCursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def execute(sql: str, params: tuple = ()) -> int:
    """Execute INSERT/UPDATE/DELETE and return lastrowid or rowcount."""
    with DBCursor() as cur:
        cur.execute(sql, params)
        return cur.lastrowid or cur.rowcount


def executemany(sql: str, data: list[tuple]) -> int:
    with DBCursor() as cur:
        cur.executemany(sql, data)
        return cur.rowcount
