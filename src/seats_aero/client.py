# src/seats_aero/client.py
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Union
import requests


JsonType = Union[dict, list]


class SeatsAeroAPIError(Exception):
    """
    Raised when the Seats.aero API returns a non-success response (non-2xx)
    that we don't want to retry or that still fails after retries.
    """

    def __init__(self, status_code: int, message: str, response_text: str = ""):
        super().__init__(f"Seats.aero API error {status_code}: {message}\n{response_text}")
        self.status_code = status_code
        self.message = message
        self.response_text = response_text


@dataclass(frozen=True)
class SeatsAeroClientConfig:
    """
    Configuration for the Seats.aero client.

    - base_url: base endpoint for partner API
    - timeout_s: request timeout in seconds
    - max_retries: how many times to retry transient failures
    - backoff_s: base delay between retries (we multiply by attempt number)
    """
    base_url: str = "https://seats.aero/partnerapi"
    timeout_s: float = 20.0
    max_retries: int = 3
    backoff_s: float = 1.0


class SeatsAeroClient:
    """
    Minimal Seats.aero HTTP client.

    Why a class?
    - It stores shared state (API key, session, base_url) once.
    - Every call automatically includes auth headers.
    - Easier to extend later (POST, specific endpoint wrappers).
    """

    def __init__(self, api_key: str, config: Optional[SeatsAeroClientConfig] = None):
        self._api_key = api_key
        self._config = config or SeatsAeroClientConfig()

        # Session reuses TCP connections (faster & cleaner than requests.get each time)
        self._session = requests.Session()

        # Default headers used on every request
        self._headers = {
            "Partner-Authorization": self._api_key,
            "Accept": "application/json",
        }

    def _build_url(self, path: str) -> str:
        """
        Join base_url and a path safely.
        """
        base = self._config.base_url.rstrip("/")
        p = path.lstrip("/")
        return f"{base}/{p}"

    def get(self, path: str, params: Optional[Dict[str, Any]] = None) -> JsonType:
        """
        Perform a GET request and return parsed JSON.

        Retries:
        - network timeouts
        - 429 Too Many Requests
        - 5xx server errors

        Raises SeatsAeroAPIError on non-retryable errors (e.g., 400, 401, 403).
        """
        url = self._build_url(path)
        params = params or {}

        last_exception: Optional[Exception] = None

        for attempt in range(self._config.max_retries + 1):
            try:
                resp = self._session.get(
                    url,
                    headers=self._headers,
                    params=params,
                    timeout=self._config.timeout_s,
                )

                # Success
                if 200 <= resp.status_code < 300:
                    return resp.json()

                # Retryable: rate limit or server errors
                if resp.status_code in (429,) or (500 <= resp.status_code < 600):
                    # Basic backoff: 1s, 2s, 3s... (configurable)
                    if attempt < self._config.max_retries:
                        sleep_s = self._config.backoff_s * (attempt + 1)
                        time.sleep(sleep_s)
                        continue

                # Non-retryable or out of retries:
                # 400 bad request, 401 unauthorized, 403 forbidden, etc.
                raise SeatsAeroAPIError(
                    status_code=resp.status_code,
                    message="Request failed",
                    response_text=resp.text[:1000],  # truncate for readability
                )

            except (requests.Timeout, requests.ConnectionError) as e:
                # Retry network failures
                last_exception = e
                if attempt < self._config.max_retries:
                    sleep_s = self._config.backoff_s * (attempt + 1)
                    time.sleep(sleep_s)
                    continue
                raise SeatsAeroAPIError(
                    status_code=0,
                    message="Network error after retries",
                    response_text=str(e),
                ) from e

            except ValueError as e:
                # JSON parse error
                raise SeatsAeroAPIError(
                    status_code=0,
                    message="Failed to parse JSON response",
                    response_text=str(e),
                ) from e

        # Should not reach here
        if last_exception:
            raise last_exception
        raise SeatsAeroAPIError(status_code=0, message="Unknown error")