"""Buttondown API utilities for synchronising data via the public API."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional
from urllib.parse import urljoin

import requests

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ButtondownAPIError(Exception):
    """Raised when Buttondown API returns an error."""


class ButtondownAPI:
    """Client for Buttondown API interactions."""

    def __init__(self, api_key: Optional[str] = None, timeout: int = 15):
        """
        Initialize Buttondown API client.

        Args:
            api_key: Optional explicit API key. Falls back to settings.
            timeout: Timeout for HTTP requests in seconds.
        """
        self.api_key = api_key or settings.buttondown_api_key
        if not self.api_key:
            raise ValueError("Buttondown API key not configured")

        self.base_url = settings.buttondown_api_base_url.rstrip("/")
        if not self.base_url:
            raise ValueError("Buttondown API base URL not configured")

        self.timeout = timeout
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json",
        }

    def iter_events(
        self,
        *,
        event_type: Optional[str] = None,
        since: Optional[datetime] = None,
        expand: Optional[List[str]] = None,
        ordering: str = "creation_date",
    ) -> Iterable[Dict]:
        """
        Yield engagement events from Buttondown.

        Args:
            event_type: Optional event type filter.
            since: Optional datetime to fetch events strictly after this moment.
            expand: Optional list of related objects to expand.
            ordering: API ordering field (defaults to chronological order).

        Yields:
            Raw event dictionaries from the Buttondown API.
        """
        base_path = "/events"
        url = urljoin(f"{self.base_url}/", base_path.lstrip("/"))
        params: Dict[str, object] = {"ordering": ordering}

        if event_type:
            params["event_type"] = event_type

        if expand:
            params["expand"] = expand

        filtered_since = False
        if since:
            params["creation_date__gt"] = self._format_datetime(since)
            filtered_since = True

        next_url: Optional[str] = url
        first_params: Optional[Dict[str, object]] = params.copy()
        fallback_attempted = False

        while next_url:
            request_params = first_params if next_url == url else None
            response = self._get(next_url, params=request_params)
            first_params = None  # Only apply query params on the first request

            if response.status_code == 400 and filtered_since and not fallback_attempted:
                # Some Buttondown deployments may not yet support creation_date__gt.
                logger.warning("Buttondown API rejected creation_date__gt filter; retrying without it")
                fallback_attempted = True
                filtered_since = False
                params.pop("creation_date__gt", None)
                next_url = url
                first_params = params.copy()
                continue

            self._raise_for_status(response)
            payload = response.json()

            for event in payload.get("results", []):
                yield event

            next_url = payload.get("next")

    def _get(self, url: str, params: Optional[Dict[str, object]] = None) -> requests.Response:
        """Perform a GET request against the API."""
        try:
            return requests.get(url, headers=self.headers, params=params, timeout=self.timeout)
        except requests.RequestException as exc:
            raise ButtondownAPIError(f"Request failed: {exc}") from exc

    def _raise_for_status(self, response: requests.Response) -> None:
        """Raise a helpful error if the response is not successful."""
        if response.status_code >= 400:
            try:
                detail = response.json()
            except ValueError:
                detail = response.text
            raise ButtondownAPIError(
                f"Buttondown API error {response.status_code}: {detail or 'no details'}"
            )

    @staticmethod
    def _format_datetime(value: datetime) -> str:
        """Return an ISO-8601 string with timezone information."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).isoformat()


def get_buttondown_client() -> ButtondownAPI:
    """Dependency helper for FastAPI to create a Buttondown API client."""
    return ButtondownAPI()
