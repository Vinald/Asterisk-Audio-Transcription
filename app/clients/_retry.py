import logging
import time

import requests

from app.core.config import settings

log = logging.getLogger(__name__)

MAX_RETRIES = settings.MAX_RETRIES
RETRY_DELAY = settings.RETRY_DELAY


def retry_request(func, max_retries=MAX_RETRIES, delay=RETRY_DELAY):
    last_error = None
    for attempt in range(max_retries):
        try:
            response = func()
            if response.status_code >= 500 and attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                log.warning("Attempt %d/%d failed: HTTP %d — retrying in %ds",
                            attempt + 1, max_retries, response.status_code, wait_time)
                time.sleep(wait_time)
                continue
            return response
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = delay * (2 ** attempt)
                log.warning("Attempt %d/%d failed: %s — retrying in %ds",
                            attempt + 1, max_retries, type(e).__name__, wait_time)
                time.sleep(wait_time)
            continue
        except Exception:
            raise
    log.error("All %d retry attempts failed", max_retries)
    raise last_error or Exception("Request failed after all retries")
