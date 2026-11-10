"""
TransitNotice – Unit Tests
Run with: python -m pytest tests/ -v
"""
import sys
import unittest
import secrets
from unittest.mock import patch, MagicMock
from datetime import timedelta

# ── Mock heavy DB / external deps for pure-logic tests ─────────────────────
# We mock mysql.connector before any module imports it, so tests that only
# exercise pure Python logic (hashing, ref generation, time conversion,
# email template building) don't require a running MySQL server.

_mock_mysql = MagicMock()
sys.modules.setdefault("mysql", _mock_mysql)
sys.modules.setdefault("mysql.connector", _mock_mysql)
sys.modules.setdefault("mysql.connector.pooling", _mock_mysql)


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestPasswordHashing(unittest.TestCase):
    """Verify bcrypt hashing and verification."""

    def test_hash_and_verify(self):
        from models.user_model import hash_password, verify_password
        plain = "TestP@ss123"
        hashed = hash_password(plain)
        self.assertNotEqual(plain, hashed)
        self.assertTrue(verify_password(plain, hashed))

    def test_wrong_password_fails(self):
        from models.user_model import hash_password, verify_password
        hashed = hash_password("CorrectHorse")
        self.assertFalse(verify_password("WrongHorse", hashed))

    def test_hash_is_unique(self):
        from models.user_model import hash_password
        h1 = hash_password("samepassword")
        h2 = hash_password("samepassword")
        self.assertNotEqual(h1, h2)  # salt should differ


class TestBookingRefGeneration(unittest.TestCase):
    """Verify booking reference format."""

    def test_reference_format(self):
        from models.booking_model import _generate_ref
        ref = _generate_ref()
        self.assertTrue(ref.startswith("TN"))
        self.assertEqual(len(ref), 14)  # "TN" + 12 chars
        self.assertTrue(ref[2:].isalnum())

    def test_references_are_unique(self):
        from models.booking_model import _generate_ref
        refs = {_generate_ref() for _ in range(100)}
        self.assertEqual(len(refs), 100)


class TestChangeDetector(unittest.TestCase):
    """Test the time-to-minutes conversion utility."""

    def test_time_string_to_minutes(self):
        from services.change_detector import _time_to_minutes
        self.assertEqual(_time_to_minutes("06:30:00"), 390)
        self.assertEqual(_time_to_minutes("23:59:00"), 1439)
        self.assertIsNone(_time_to_minutes(None))

    def test_timedelta_to_minutes(self):
        from services.change_detector import _time_to_minutes
        td = timedelta(hours=5, minutes=45)
        self.assertEqual(_time_to_minutes(td), 345)

    def test_zero_time(self):
        from services.change_detector import _time_to_minutes
        self.assertEqual(_time_to_minutes("00:00:00"), 0)

    def test_midnight(self):
        from services.change_detector import _time_to_minutes
        self.assertEqual(_time_to_minutes("12:00:00"), 720)


class TestBaseScraper(unittest.TestCase):
    """Test the base scraper result builder."""

    def test_result_builder(self):
        from scrapers.base_scraper import BaseScraper

        class DummyScraper(BaseScraper):
            provider = "TEST"
            def collect(self):
                return self._result(fetched=10, inserted=3, updated=2, changes=1)

        scraper = DummyScraper()
        result = scraper.collect()
        self.assertEqual(result["records_fetched"], 10)
        self.assertEqual(result["records_inserted"], 3)
        self.assertEqual(result["records_updated"], 2)
        self.assertEqual(result["changes_detected"], 1)
        self.assertEqual(result["errors"], [])

    def test_result_with_errors(self):
        from scrapers.base_scraper import BaseScraper

        class ErrorScraper(BaseScraper):
            provider = "ERR"
            def collect(self):
                return self._result(errors=["timeout", "bad data"])

        result = ErrorScraper().collect()
        self.assertEqual(result["records_fetched"], 0)
        self.assertEqual(len(result["errors"]), 2)


class TestMTCScraperDisabled(unittest.TestCase):
    """MTC scraper should return error when not authorised."""

    def test_collection_disabled(self):
        from scrapers.mtc_scraper import MTCScraper
        scraper = MTCScraper()
        self.assertFalse(scraper.is_authorized)
        result = scraper.collect()
        self.assertEqual(result["records_fetched"], 0)
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("Not authorized", result["errors"][0])


class TestTNSTCScraperDisabled(unittest.TestCase):

    def test_collection_disabled(self):
        from scrapers.tnstc_scraper import TNSTCScraper
        scraper = TNSTCScraper()
        self.assertFalse(scraper.is_authorized)
        result = scraper.collect()
        self.assertIn("Not authorized", result["errors"][0])


class TestSETCScraperDisabled(unittest.TestCase):

    def test_collection_disabled(self):
        from scrapers.setc_scraper import SETCScraper
        scraper = SETCScraper()
        self.assertFalse(scraper.is_authorized)
        result = scraper.collect()
        self.assertIn("Not authorized", result["errors"][0])


class TestCMRLScraperDisabled(unittest.TestCase):

    def test_collection_disabled(self):
        from scrapers.cmrl_scraper import CMRLScraper
        scraper = CMRLScraper()
        self.assertFalse(scraper.is_authorized)
        result = scraper.collect()
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("not authorized", result["errors"][0].lower())


class TestEmailTemplates(unittest.TestCase):
    """Smoke test email template builders."""

    def test_schedule_change_email(self):
        from services.email_service import build_schedule_change_email
        subject, html, text = build_schedule_change_email(
            user_name="Arun Kumar",
            provider="MTC",
            route_number="21C",
            origin="T.Nagar",
            destination="Broadway",
            old_time="06:30",
            new_time="07:00",
            reason="Maintenance",
            booking_ref="TN123456789012",
        )
        self.assertIn("TransitNotice", subject)
        self.assertIn("21C", subject)
        self.assertIn("06:30", html)
        self.assertIn("07:00", html)
        self.assertIn("Arun Kumar", text)
        self.assertIn("TN123456789012", html)

    def test_booking_confirmation_email(self):
        from services.email_service import build_booking_confirmation_email
        subject, html, text = build_booking_confirmation_email(
            user_name="Priya",
            booking_ref="TN987654321098",
            provider="CMRL",
            route_number="Blue Line",
            origin="Alandur",
            destination="Airport",
            journey_date="2026-12-15",
            departure_time="09:30",
            passenger_count=2,
        )
        self.assertIn("TN987654321098", subject)
        self.assertIn("Alandur", html)
        self.assertIn("Blue Line", text)

    def test_schedule_change_email_empty_reason(self):
        from services.email_service import build_schedule_change_email
        _, html, text = build_schedule_change_email(
            user_name="Test",
            provider="TNSTC",
            route_number="100",
            origin="A",
            destination="B",
            old_time="08:00",
            new_time="08:30",
            reason="",
            booking_ref="TN000000000000",
        )
        self.assertIn("Schedule updated by operator", html)


class TestConfigLoading(unittest.TestCase):
    """Verify config defaults."""

    def test_config_has_required_attrs(self):
        from config import DevelopmentConfig
        cfg = DevelopmentConfig()
        self.assertEqual(cfg.DB_CHARSET, "utf8mb4")
        self.assertEqual(cfg.SCHEDULER_INTERVAL_MINUTES, 10)
        self.assertTrue(hasattr(cfg, "SECRET_KEY"))
        self.assertTrue(hasattr(cfg, "DB_HOST"))

    def test_get_config_returns_instance(self):
        from config import get_config
        cfg = get_config()
        self.assertIsInstance(cfg, object)
        self.assertTrue(hasattr(cfg, "DB_NAME"))
        self.assertEqual(cfg.DB_NAME, "transitnotice")

    def test_development_debug_on(self):
        from config import DevelopmentConfig
        self.assertTrue(DevelopmentConfig.DEBUG)

    def test_production_debug_off(self):
        from config import ProductionConfig
        self.assertFalse(ProductionConfig.DEBUG)

    def test_default_timezone(self):
        from config import Config
        self.assertEqual(Config.TIMEZONE, "Asia/Kolkata")

    def test_scheduler_defaults(self):
        from config import Config
        self.assertEqual(Config.SCHEDULER_INTERVAL_MINUTES, 10)
        self.assertTrue(Config.SCHEDULER_ENABLED)


class TestScraperHeaders(unittest.TestCase):
    """Verify scraper sends proper User-Agent."""

    def test_user_agent_contains_bot_name(self):
        from scrapers.base_scraper import HEADERS
        ua = HEADERS["User-Agent"]
        self.assertIn("TransitNotice-Bot", ua)
        self.assertIn("1.0", ua)
        self.assertIn("contact", ua.lower())


if __name__ == "__main__":
    unittest.main()
