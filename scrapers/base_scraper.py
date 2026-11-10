
"""
Base scraper for TransitNotice.

Features:
- Shared HTTP session
- Automatic retries
- robots.txt checking
- Request timeout
- Rate limiting
- Error handling
- Standard result format
"""

import time
import logging
import urllib.robotparser

from urllib.parse import urlparse
from urllib.error import URLError

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "TransitNotice-Bot/1.0 "
        "(+https://transitnotice.in/bot)"
    ),
    "Accept": "text/html,application/json",
    "Accept-Language": "en-IN,en;q=0.9,ta;q=0.8",
}

DEFAULT_TIMEOUT = 20
DEFAULT_DELAY = 1.5


def build_session():

    session = requests.Session()

    retry = Retry(
        total=3,
        connect=3,
        read=2,
        backoff_factor=1.5,
        status_forcelist=[
            429,
            500,
            502,
            503,
            504
        ],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True
    )

    adapter = HTTPAdapter(
        max_retries=retry
    )

    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update(HEADERS)

    return session


class BaseScraper:
    """
    Common base class for all transport scrapers.

    Subclasses should implement collect().
    """

    provider = "UNKNOWN"
    source_id = None

    is_authorized = False

    def __init__(self):

        self.session = build_session()

        self.robots_cache = {}

        self.last_request_time = 0

    # -------------------------------------------------
    # ROBOTS.TXT CHECK
    # -------------------------------------------------

    def check_robots(self, url):

        parsed = urlparse(url)

        robots_url = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}/robots.txt"
        )

        if robots_url not in self.robots_cache:

            rp = urllib.robotparser.RobotFileParser()

            try:

                response = self.session.get(
                    robots_url,
                    timeout=DEFAULT_TIMEOUT
                )

                if response.status_code != 200:
                    logger.warning(
                        "[%s] Cannot verify robots.txt: HTTP %s",
                        self.provider,
                        response.status_code
                    )
                    return False

                rp.parse(response.text.splitlines())

                self.robots_cache[robots_url] = rp

            except requests.exceptions.RequestException as exc:

                logger.error(
                    "[%s] robots.txt error: %s",
                    self.provider,
                    exc
                )

                return False

        return self.robots_cache[
            robots_url
        ].can_fetch(
            HEADERS["User-Agent"],
            url
        )

    # -------------------------------------------------
    # RATE LIMITING
    # -------------------------------------------------

    def rate_limit(self, delay=DEFAULT_DELAY):

        elapsed = time.monotonic() - self.last_request_time

        remaining = delay - elapsed

        if remaining > 0:
            time.sleep(remaining)

        self.last_request_time = time.monotonic()

    # -------------------------------------------------
    # HTTP GET
    # -------------------------------------------------

    def get(self, url, params=None, delay=DEFAULT_DELAY):

        if not self.check_robots(url):

            logger.warning(
                "[%s] Access not permitted by robots policy: %s",
                self.provider,
                url
            )

            return None

        self.rate_limit(delay)

        try:

            response = self.session.get(
                url,
                params=params,
                timeout=DEFAULT_TIMEOUT
            )

            response.raise_for_status()

            return response

        except requests.exceptions.Timeout:

            logger.error(
                "[%s] Request timeout: %s",
                self.provider,
                url
            )

        except requests.exceptions.HTTPError as exc:

            status = (
                exc.response.status_code
                if exc.response is not None
                else "Unknown"
            )

            logger.error(
                "[%s] HTTP error %s: %s",
                self.provider,
                status,
                url
            )

        except requests.exceptions.RequestException as exc:

            logger.error(
                "[%s] Request failed: %s",
                self.provider,
                exc
            )

        return None

    # -------------------------------------------------
    # STANDARD RESULT
    # -------------------------------------------------

    def result(
        self,
        fetched=0,
        inserted=0,
        updated=0,
        changes=0,
        errors=None,
        status=None
    ):

        if errors is None:
            errors = []

        if status is None:
            status = (
                "connected"
                if not errors
                else "failed"
            )

        return {
            "provider": self.provider,
            "status": status,
            "records_fetched": fetched,
            "records_inserted": inserted,
            "records_updated": updated,
            "changes_detected": changes,
            "errors": errors
        }

    # -------------------------------------------------
    # COLLECTION INTERFACE
    # -------------------------------------------------

    def collect(self):

        raise NotImplementedError(
            "Subclasses must implement collect()"
        )

    # -------------------------------------------------
    # CLOSE SESSION
    # -------------------------------------------------

    def close(self):

        self.session.close()
