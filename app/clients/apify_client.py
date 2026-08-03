"""
Generic Apify API client.

This is a thin, reusable wrapper around Apify's public REST API:
https://docs.apify.com/api/v2

It knows nothing about any specific Actor, dataset, or use case — it
only knows how to authenticate, run an Actor synchronously, fetch a
dataset's items, retry on transient failures, and translate Apify/HTTP
errors into this project's standard exception types.

Wiring this client up to a specific Actor (i.e. deciding *what* it
runs) is a separate, deliberate decision made at the call site — see
`app/clients/live_provider_client.py`. This module intentionally does
not reference any Actor ID, scraping target, or protected/unauthorized
data source.
"""
import asyncio
import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.exceptions.errors import (
    InvalidParametersError,
    ProviderParsingError,
    ProviderRateLimitedError,
    ProviderUnavailableError,
)

logger = logging.getLogger("tiktok_ads_api.apify_client")

_APIFY_BASE_URL = "https://api.apify.com/v2"


class ApifyClient:
    """Generic async client for the Apify platform API.

    Usage:
        client = ApifyClient(settings)
        items = await client.run_actor_sync_get_dataset_items(
            actor_id="<owner>/<actor-name-or-id>",
            run_input={...},
        )
    """

    def __init__(
        self,
        settings: Settings,
        *,
        timeout_seconds: float = 60.0,
        max_retries: int = 2,
        retry_backoff_seconds: float = 1.5,
    ) -> None:
        if not settings.apify_api_token:
            logger.warning(
                "ApifyClient instantiated without APIFY_API_TOKEN configured. "
                "Every call will fail until this is set."
            )
        self._token = settings.apify_api_token
        self._timeout_seconds = timeout_seconds
        self._max_retries = max_retries
        self._retry_backoff_seconds = retry_backoff_seconds

    def _auth_params(self) -> dict[str, str]:
        if not self._token:
            raise InvalidParametersError(
                "Apify integration is not configured.",
                {"missing": "APIFY_API_TOKEN"},
            )
        return {"token": self._token}

    async def _request_with_retries(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Issue an HTTP request with retry-on-transient-failure semantics.

        Retries on: network errors, timeouts, and HTTP 5xx / 429.
        Does NOT retry on 4xx (other than 429), since those indicate a
        problem with the request itself (bad Actor ID, bad input, auth
        failure) that a retry won't fix.
        """
        last_exc: Exception | None = None

        for attempt in range(self._max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                    response = await client.request(
                        method, url, params=params, json=json_body
                    )

                if response.status_code == 429:
                    logger.warning(
                        "Apify rate limit hit (attempt %d/%d) for %s",
                        attempt + 1,
                        self._max_retries + 1,
                        url,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                        continue
                    raise ProviderRateLimitedError(
                        "Apify API rate limit exceeded.", {"url": url}
                    )

                if response.status_code >= 500:
                    logger.warning(
                        "Apify server error %s (attempt %d/%d) for %s",
                        response.status_code,
                        attempt + 1,
                        self._max_retries + 1,
                        url,
                    )
                    if attempt < self._max_retries:
                        await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                        continue
                    raise ProviderUnavailableError(
                        f"Apify API returned server error {response.status_code}.",
                        {"url": url, "status_code": response.status_code},
                    )

                if response.status_code >= 400:
                    # Non-retryable client error: bad actor id, bad input,
                    # invalid/expired token, etc.
                    logger.warning(
                        "Apify client error %s for %s: %s",
                        response.status_code,
                        url,
                        response.text[:500],
                    )
                    raise ProviderUnavailableError(
                        f"Apify API rejected the request with status "
                        f"{response.status_code}.",
                        {"url": url, "status_code": response.status_code},
                    )

                return response

            except (httpx.TimeoutException, httpx.TransportError) as exc:
                last_exc = exc
                logger.warning(
                    "Apify network error (attempt %d/%d) for %s: %s",
                    attempt + 1,
                    self._max_retries + 1,
                    url,
                    exc,
                )
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_backoff_seconds * (attempt + 1))
                    continue

        raise ProviderUnavailableError(
            "Apify API is currently unreachable.",
            {"url": url, "cause": str(last_exc) if last_exc else "unknown"},
        )

    async def run_actor_sync_get_dataset_items(
        self,
        *,
        actor_id: str,
        run_input: dict[str, Any] | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Run an Actor synchronously and return its resulting dataset items.

        Wraps Apify's `run-sync-get-dataset-items` endpoint, which starts
        an Actor run, waits for it to finish, and returns the dataset
        items directly — no separate polling/dataset-fetch step needed.

        `actor_id` should be in Apify's `owner~actor-name` or raw actor
        ID form, as documented at https://docs.apify.com/api/v2.
        """
        url = f"{_APIFY_BASE_URL}/acts/{actor_id}/run-sync-get-dataset-items"
        params = self._auth_params()
        if limit is not None:
            params["limit"] = str(limit)

        response = await self._request_with_retries(
            "POST", url, params=params, json_body=run_input or {}
        )

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderParsingError(
                "Failed to parse JSON response from Apify.", {"url": url}
            ) from exc

        if not isinstance(data, list):
            raise ProviderParsingError(
                "Unexpected response shape from Apify: expected a list of "
                "dataset items.",
                {"url": url, "received_type": type(data).__name__},
            )

        return data

    async def get_dataset_items(
        self, *, dataset_id: str, limit: int | None = None, offset: int | None = None
    ) -> list[dict[str, Any]]:
        """Fetch items from an existing dataset (e.g. from a prior async run)."""
        url = f"{_APIFY_BASE_URL}/datasets/{dataset_id}/items"
        params = self._auth_params()
        if limit is not None:
            params["limit"] = str(limit)
        if offset is not None:
            params["offset"] = str(offset)

        response = await self._request_with_retries("GET", url, params=params)

        try:
            data = response.json()
        except ValueError as exc:
            raise ProviderParsingError(
                "Failed to parse JSON response from Apify.", {"url": url}
            ) from exc

        if not isinstance(data, list):
            raise ProviderParsingError(
                "Unexpected response shape from Apify: expected a list of "
                "dataset items.",
                {"url": url, "received_type": type(data).__name__},
            )

        return data
