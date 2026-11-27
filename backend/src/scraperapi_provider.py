"""
ScraperAPI fetching provider for ScrapeScout.

Provides a reusable, resilient HTTP fetching layer via ScraperAPI (https://api.scraperapi.com/).
Supports multiple website sources while keeping website-specific parsing logic separate.

Security & compliance:
- Reads the API key strictly from the SCRAPER_API_KEY environment variable.
- Redacts the API key from all logs, exceptions, and error messages.
- Does not bypass platform access controls, CAPTCHAs, or authentication checkpoints.
- Does not fall back silently to direct scraping when the provider fails.
"""

import os
import logging
import re
from typing import Optional, Dict, Any
from urllib.parse import urlparse

import requests

logger = logging.getLogger("scrapescout.scraperapi")

SCRAPER_API_URL = "https://api.scraperapi.com/"
DEFAULT_TIMEOUT = 30


class ScraperAPIError(Exception):
    """Base exception for ScraperAPI provider errors."""


class ScraperAPIConfigError(ScraperAPIError):
    """Raised when the ScraperAPI key is missing or invalid."""


class ScraperAPIAccessError(ScraperAPIError):
    """Raised when the target page is restricted, redirected, or blocks access."""


def redact_api_key(text: str, api_key: Optional[str] = None) -> str:
    """
    Remove or redact sensitive API keys from strings, logs, or error messages.
    """
    if not text:
        return text

    redacted = text
    # Redact explicit key if known
    if api_key and len(api_key.strip()) > 3:
        redacted = redacted.replace(api_key.strip(), "[REDACTED]")

    # Redact any api_key query parameters in URLs: api_key=xyz
    redacted = re.sub(r"(api_key=)[^& \t\r\n]+", r"\1[REDACTED]", redacted, flags=re.IGNORECASE)
    return redacted


class ScraperAPIClient:
    """
    Client for fetching public webpages via ScraperAPI.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        base_url: str = SCRAPER_API_URL,
    ):
        # Allow explicit injection or read from environment
        resolved_key = api_key or os.getenv("SCRAPER_API_KEY")
        if resolved_key:
            resolved_key = resolved_key.strip()

        self._api_key = resolved_key
        self.timeout = timeout
        self.base_url = base_url

    @property
    def is_configured(self) -> bool:
        """Return True if an API key is present."""
        return bool(self._api_key)

    def fetch(
        self,
        url: str,
        render_js: bool = False,
        country_code: Optional[str] = None,
        extra_params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        Fetch webpage HTML using ScraperAPI proxy service.

        Args:
            url: The target web page URL (HTTP or HTTPS).
            render_js: Whether to request headless browser rendering (ScraperAPI 'render=true').
            country_code: Optional 2-letter country code for geo-targeting (e.g. 'us').
            extra_params: Additional query parameters for ScraperAPI.
            timeout: Request timeout in seconds.

        Returns:
            The raw HTML content of the target page.

        Raises:
            ValueError: If target URL is invalid or malformed.
            ScraperAPIConfigError: If SCRAPER_API_KEY is not configured.
            ScraperAPIAccessError: If access is blocked, restricted, redirected, or checkpointed.
            ScraperAPIError: If provider returns HTTP errors or request times out.
        """
        if not self._api_key:
            raise ScraperAPIConfigError(
                "SCRAPER_API_KEY environment variable is not configured. "
                "Please set SCRAPER_API_KEY before using the ScraperAPI provider."
            )

        # Validate target URL
        if not url or not isinstance(url, str) or any(c.isspace() for c in url):
            raise ValueError("A valid HTTP or HTTPS URL is required.")

        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                raise ValueError("A valid HTTP or HTTPS URL is required.")
            if not parsed.netloc or not parsed.hostname:
                raise ValueError("A valid HTTP or HTTPS URL is required.")
            if parsed.username is not None or parsed.password is not None:
                raise ValueError("A valid HTTP or HTTPS URL without embedded credentials is required.")
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"Invalid URL structure: {exc}") from exc

        request_timeout = timeout if timeout is not None else self.timeout

        params: Dict[str, Any] = {
            "api_key": self._api_key,
            "url": url,
        }

        if render_js:
            params["render"] = "true"

        if country_code:
            params["country_code"] = country_code.lower()

        if extra_params:
            for k, v in extra_params.items():
                if k not in params:
                    params[k] = v

        try:
            response = requests.get(
                self.base_url,
                params=params,
                timeout=request_timeout,
            )
        except requests.Timeout as exc:
            safe_msg = redact_api_key(str(exc), self._api_key)
            logger.error("ScraperAPI request timed out fetching %s: %s", url, safe_msg)
            raise ScraperAPIError(f"ScraperAPI request timed out after {request_timeout}s.") from exc
        except requests.RequestException as exc:
            safe_msg = redact_api_key(str(exc), self._api_key)
            logger.error("ScraperAPI network error fetching %s: %s", url, safe_msg)
            raise ScraperAPIError(f"ScraperAPI connection error: {safe_msg}") from exc

        # Handle HTTP status codes from ScraperAPI
        status_code = response.status_code

        # ScraperAPI specific error codes:
        # 401/403: Invalid API key or unauthorized
        # 429: Rate limit exceeded / concurrency limit reached
        # 500: Failed to fetch target page after multiple retries
        if status_code in (401, 403):
            raise ScraperAPIConfigError(
                f"ScraperAPI authentication failed (HTTP {status_code}). Please check your SCRAPER_API_KEY."
            )

        if status_code == 429:
            raise ScraperAPIError(
                "ScraperAPI concurrency limit or rate limit exceeded. Please throttle requests."
            )

        if 300 <= status_code < 400:
            raise ScraperAPIAccessError(
                f"Target website returned a redirect (HTTP {status_code}). Not followed automatically."
            )

        if status_code >= 400:
            raise ScraperAPIError(
                f"ScraperAPI failed to retrieve the page (HTTP {status_code})."
            )

        page_text = response.text or ""
        page_text_lower = page_text.lower()

        # Check for security checkpoints or human verification markers
        restricted_markers = (
            "vercel security checkpoint",
            "verify you are human",
            "security checkpoint",
            "cloudflare ray id",
            "attention required! | cloudflare",
        )

        if any(marker in page_text_lower for marker in restricted_markers):
            raise ScraperAPIAccessError(
                "A security checkpoint or bot verification screen was detected on the target page. "
                "The page was not processed."
            )

        return page_text


def fetch_page_via_scraperapi(
    url: str,
    api_key: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    render_js: bool = False,
    country_code: Optional[str] = None,
) -> str:
    """
    Convenience function to fetch a page using ScraperAPI.
    Suitable as a drop-in 'fetcher' function for scrapers.
    """
    client = ScraperAPIClient(api_key=api_key, timeout=timeout)
    return client.fetch(
        url=url,
        render_js=render_js,
        country_code=country_code,
    )
