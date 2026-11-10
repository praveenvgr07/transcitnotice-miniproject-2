"""
SETC scraper – DISABLED pending authorization.

SETC (State Express Transport Corporation) does not currently publish
an open machine-readable API or GTFS feed.  The official website at
https://www.setc.tn.gov.in must be reviewed for terms of use.

This integration remains DISABLED until official authorization is obtained.
"""
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class SETCScraper(BaseScraper):
    provider = "SETC"
    is_authorized = False

    SOURCE_URL = "https://www.setc.tn.gov.in"

    def collect(self) -> dict:
        if not self.is_authorized:
            logger.info(
                "[SETC] Collection DISABLED – awaiting authorization. "
                "Review %s before enabling.", self.SOURCE_URL
            )
            return self._result(errors=["Not authorized – collection disabled."])
        return self._result(errors=["collect() not yet implemented."])
