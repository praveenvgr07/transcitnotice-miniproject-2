
"""
MTC Chennai scraper for TransitNotice.

MTC collection remains disabled until official
authorization and a permitted data endpoint are verified.
"""

import logging

from .base_scraper import BaseScraper


logger = logging.getLogger(__name__)


class MTCScraper(BaseScraper):

    provider = "MTC"

    # Keep False until official permission is obtained.
    is_authorized = False

    SOURCE_URL = "https://mtcbus.tn.gov.in"

    def collect(self):

        logger.info(
            "[MTC] Starting data collection"
        )

        # -----------------------------------------
        # AUTHORIZATION CHECK
        # -----------------------------------------

        if not self.is_authorized:

            message = (
                "MTC data collection is disabled. "
                "Awaiting official authorization."
            )

            logger.warning(
                "[MTC] %s",
                message
            )

            return self.result(
                errors=[message],
                status="pending_auth"
            )

        # -----------------------------------------
        # ENDPOINT CONFIGURATION
        # -----------------------------------------

        # Configure this only with an officially
        # approved machine-readable endpoint.

        permitted_endpoint = None

        if not permitted_endpoint:

            message = (
                "Authorization is configured, "
                "but no approved data endpoint exists."
            )

            return self.result(
                errors=[message],
                status="not_configured"
            )

        # -----------------------------------------
        # FETCH DATA
        # -----------------------------------------

        response = self.get(
            permitted_endpoint
        )

        if response is None:

            return self.result(
                errors=["Unable to fetch MTC data."],
                status="failed"
            )

        # -----------------------------------------
        # PARSE DATA
        # -----------------------------------------

        try:

            data = response.json()

            if not isinstance(data, list):

                raise ValueError(
                    "Expected a JSON list of records."
                )

            records_fetched = len(data)

            logger.info(
                "[MTC] Retrieved %s records",
                records_fetched
            )

            # Database integration should be added here.
            # Do not report inserts or updates until
            # records are actually saved.

            return self.result(
                fetched=records_fetched,
                inserted=0,
                updated=0,
                changes=0,
                status="connected"
            )

        except (ValueError, requests.exceptions.JSONDecodeError) as exc:

            logger.error(
                "[MTC] Invalid JSON response: %s",
                exc
            )

            return self.result(
                errors=["Invalid JSON response from MTC endpoint."],
                status="failed"
            )
