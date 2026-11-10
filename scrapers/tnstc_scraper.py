"""
TNSTC scraper – DISABLED pending authorization.

TNSTC (Tamil Nadu State Transport Corporation) does not currently publish
an open machine-readable API or GTFS feed.  The official website at
https://www.tnstc.in must be reviewed for:
  - robots.txt rules
  - Terms of Service / data licensing
  - Any open-data programme

This integration remains DISABLED until official authorization is obtained.
"""
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)


class TNSTCScraper(BaseScraper):
    provider = "TNSTC"
    is_authorized = False

    SOURCE_URL = "https://www.tnstc.in"

    def collect(self) -> dict:
        if not self.is_authorized:
            logger.info(
                "[TNSTC] Collection DISABLED – awaiting authorization. "
                "Review %s before enabling.", self.SOURCE_URL
            )
            return self._result(errors=["Not authorized – collection disabled."])
        return self._result(errors=["collect() not yet implemented."])
