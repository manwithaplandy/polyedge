"""Rate limit handling for external APIs with graceful degradation."""

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Optional, TypeVar

import httpx

from src.config import get_settings

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RateLimitError(Exception):
    """Raised when an API is rate limited."""

    def __init__(self, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s" if retry_after else "Rate limited")


class RateLimitedClient:
    """
    Wrapper that tracks rate limits and provides graceful degradation.

    Instead of raising exceptions when rate limited, this class:
    - Tracks when each API was rate limited
    - Returns None instead of crashing
    - Implements exponential backoff
    - Logs degraded state for observability
    """

    def __init__(self, name: str):
        self.name = name
        self.rate_limited_until: Optional[datetime] = None
        self.consecutive_failures = 0
        self.last_error: Optional[str] = None

    def is_available(self) -> bool:
        """Check if API is available (not currently rate limited)."""
        if self.rate_limited_until is None:
            return True
        if datetime.utcnow() >= self.rate_limited_until:
            # Backoff period expired, reset state
            self.rate_limited_until = None
            self.consecutive_failures = 0
            logger.info(f"{self.name} API: Rate limit backoff expired, resuming")
            return True
        return False

    def get_status(self) -> dict:
        """Get current status of this API client."""
        if self.rate_limited_until:
            return {
                "available": False,
                "rate_limited_until": self.rate_limited_until.isoformat(),
                "reason": "rate_limited",
                "last_error": self.last_error,
            }
        return {
            "available": True,
            "rate_limited_until": None,
            "reason": None,
            "last_error": self.last_error,
        }

    def mark_rate_limited(self, retry_after: Optional[int] = None) -> None:
        """Mark this API as rate limited."""
        settings = get_settings()

        # Use retry-after header if provided, otherwise use exponential backoff
        if retry_after:
            backoff_seconds = retry_after
        else:
            # Exponential backoff: 15min, 30min, 60min, etc.
            base_minutes = settings.api_retry_after_minutes
            backoff_seconds = base_minutes * 60 * (2 ** self.consecutive_failures)
            # Cap at 2 hours
            backoff_seconds = min(backoff_seconds, 7200)

        self.rate_limited_until = datetime.utcnow() + timedelta(seconds=backoff_seconds)
        self.consecutive_failures += 1

        logger.warning(
            f"{self.name} API: Rate limited. Backing off until {self.rate_limited_until}. "
            f"Consecutive failures: {self.consecutive_failures}"
        )

    def mark_success(self) -> None:
        """Mark a successful API call, reset failure counters."""
        if self.consecutive_failures > 0:
            logger.info(f"{self.name} API: Request succeeded, resetting failure counter")
        self.consecutive_failures = 0
        self.last_error = None

    async def execute(
        self,
        func: Callable[..., T],
        *args,
        default: Optional[T] = None,
        **kwargs,
    ) -> Optional[T]:
        """
        Execute an async function with rate limit handling.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            default: Value to return if rate limited or error (default: None)
            **kwargs: Keyword arguments for func

        Returns:
            Result of func, or default if rate limited/error
        """
        if not self.is_available():
            logger.debug(f"{self.name} API: Skipping call, rate limited until {self.rate_limited_until}")
            return default

        try:
            result = await func(*args, **kwargs)
            self.mark_success()
            return result

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # Rate limited
                retry_after = e.response.headers.get("retry-after")
                retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else None
                self.mark_rate_limited(retry_seconds)
                self.last_error = f"HTTP 429: Rate limited"
                return default
            else:
                # Other HTTP error
                self.last_error = f"HTTP {e.response.status_code}: {e.response.reason_phrase}"
                logger.error(f"{self.name} API: HTTP error {e.response.status_code}")
                # Don't back off for non-429 errors, but track the error
                return default

        except httpx.TimeoutException:
            self.last_error = "Request timeout"
            logger.error(f"{self.name} API: Request timeout")
            return default

        except httpx.RequestError as e:
            self.last_error = f"Request error: {str(e)}"
            logger.error(f"{self.name} API: Request error - {e}")
            return default

        except Exception as e:
            self.last_error = f"Unexpected error: {str(e)}"
            logger.error(f"{self.name} API: Unexpected error - {e}")
            return default


# Global rate limiter instances for each API
_rate_limiters: dict[str, RateLimitedClient] = {}


def get_rate_limiter(name: str) -> RateLimitedClient:
    """Get or create a rate limiter for the given API name."""
    if name not in _rate_limiters:
        _rate_limiters[name] = RateLimitedClient(name)
    return _rate_limiters[name]


def get_all_api_status() -> dict[str, dict]:
    """Get status of all tracked APIs."""
    return {name: limiter.get_status() for name, limiter in _rate_limiters.items()}
