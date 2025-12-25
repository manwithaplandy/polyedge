"""Polymarket data source with real and mock implementations."""

import json
import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx

from src.config import get_settings
from src.models.market import Market, MarketTier
from src.services.data_sources.base import DataSourceBase
from src.services.data_sources.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


def is_market_current(market: Market) -> bool:
    """
    Check if a market is current and tradeable.

    Filters out:
    - Closed markets
    - Archived markets
    - Markets with end_date in the past
    - Markets not accepting orders
    """
    # Check explicit closed/archived status
    if market.closed:
        return False
    if market.archived:
        return False
    if not market.accepting_orders:
        return False

    # Check if end_date is in the past
    if market.end_date:
        end_date = market.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        if end_date < datetime.now(timezone.utc):
            return False

    return True


class PolymarketDataSource(DataSourceBase):
    """Real Polymarket Gamma API data source."""

    def __init__(self, base_url: Optional[str] = None):
        settings = get_settings()
        self.base_url = base_url or settings.polymarket_api_url
        self.timeout = 30.0
        self.rate_limiter = get_rate_limiter("polymarket")

    async def health_check(self) -> bool:
        """Check if Polymarket API is available."""
        if not self.rate_limiter.is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/markets?limit=1")
                return response.status_code == 200
        except Exception:
            return False

    async def fetch(self, **kwargs) -> list[Market]:
        """Fetch markets from Polymarket API."""
        return await self.get_markets(**kwargs)

    async def _fetch_markets_internal(
        self,
        active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Market]:
        """Internal method to fetch markets."""
        params = {"limit": limit, "offset": offset}
        if active is not None:
            params["active"] = str(active).lower()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/markets", params=params)
            response.raise_for_status()
            data = response.json()

        markets = []
        for m in data:
            try:
                market = Market(**m)
                markets.append(market.with_computed_fields())
            except Exception as e:
                logger.warning(f"Failed to parse market {m.get('id', 'unknown')}: {e}")
        return markets

    async def get_markets(
        self,
        active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0,
        filter_current: bool = True,
    ) -> list[Market]:
        """
        Fetch markets from Gamma API with rate limit handling.

        Args:
            active: Filter by Polymarket's active status
            limit: Max markets to return
            offset: Pagination offset
            filter_current: If True, filters out closed/expired markets locally
        """
        result = await self.rate_limiter.execute(
            self._fetch_markets_internal,
            active=active,
            limit=limit,
            offset=offset,
            default=[],
        )
        markets = result or []

        # Apply local filtering for current markets
        # This catches closed/expired markets that the API doesn't filter properly
        if filter_current:
            before_count = len(markets)
            markets = [m for m in markets if is_market_current(m)]
            filtered_count = before_count - len(markets)
            if filtered_count > 0:
                logger.debug(f"Filtered out {filtered_count} non-current markets")

        return markets

    async def _fetch_market_internal(self, market_id: str) -> Optional[Market]:
        """Internal method to fetch a single market."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/markets/{market_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        market = Market(**data)
        return market.with_computed_fields()

    async def get_market(self, market_id: str) -> Optional[Market]:
        """Fetch a single market by ID with rate limit handling."""
        return await self.rate_limiter.execute(
            self._fetch_market_internal,
            market_id,
            default=None,
        )

    async def get_market_by_slug(self, slug: str, require_current: bool = True) -> Optional[Market]:
        """
        Fetch a market by its slug.

        Args:
            slug: Market URL slug
            require_current: If True, returns None for closed/expired markets
        """
        result = await self.rate_limiter.execute(
            self._fetch_market_by_slug_internal,
            slug,
            default=None,
        )

        # Validate market is current if required
        if result and require_current and not is_market_current(result):
            logger.info(f"Market '{slug}' is closed or expired, skipping")
            return None

        return result

    async def _fetch_market_by_slug_internal(self, slug: str) -> Optional[Market]:
        """Internal method to fetch a market by slug."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.base_url}/markets",
                params={"slug": slug, "limit": 1},
            )
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()

        if not data:
            return None

        market = Market(**data[0])
        return market.with_computed_fields()


class MockPolymarketDataSource(DataSourceBase):
    """Mock Polymarket data source for development."""

    # Realistic political market data based on actual Polymarket markets
    MOCK_MARKETS = [
        {
            "id": "mock-trump-2024",
            "condition_id": "0x1234567890abcdef1234567890abcdef12345678",
            "question": "Will Donald Trump win the 2024 presidential election?",
            "slug": "will-donald-trump-win-2024",
            "description": "This market resolves to Yes if Donald Trump wins the 2024 US Presidential Election.",
            "category": "Politics",
            "tags": ["politics", "us-elections", "2024"],
            "active": True,
            "closed": False,
            "volume": 15_500_000,
            "volume_24h": 450_000,
            "liquidity": 2_500_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.52, 0.48]",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-11-06T00:00:00Z",
        },
        {
            "id": "mock-harris-2024",
            "condition_id": "0xabcdef1234567890abcdef1234567890abcdef12",
            "question": "Will Kamala Harris win the 2024 presidential election?",
            "slug": "will-kamala-harris-win-2024",
            "description": "This market resolves to Yes if Kamala Harris wins the 2024 US Presidential Election.",
            "category": "Politics",
            "tags": ["politics", "us-elections", "2024"],
            "active": True,
            "closed": False,
            "volume": 12_300_000,
            "volume_24h": 380_000,
            "liquidity": 1_800_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.47, 0.53]",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2024-11-06T00:00:00Z",
        },
        {
            "id": "mock-senate-control",
            "condition_id": "0x567890abcdef1234567890abcdef1234567890ab",
            "question": "Which party will control the Senate after 2024 elections?",
            "slug": "senate-control-2024",
            "description": "This market resolves based on which party controls the Senate after January 2025.",
            "category": "Politics",
            "tags": ["politics", "us-elections", "congress"],
            "active": True,
            "closed": False,
            "volume": 3_200_000,
            "volume_24h": 95_000,
            "liquidity": 450_000,
            "outcomes": ["Republican", "Democrat"],
            "outcome_prices": "[0.58, 0.42]",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2025-01-03T00:00:00Z",
        },
        {
            "id": "mock-fed-rate-jan",
            "condition_id": "0x890abcdef1234567890abcdef1234567890abcdef",
            "question": "Will the Fed cut rates in January 2025?",
            "slug": "fed-rate-cut-january-2025",
            "description": "Resolves Yes if the Federal Reserve announces a rate cut at the January 2025 FOMC meeting.",
            "category": "Economics",
            "tags": ["economics", "federal-reserve", "interest-rates"],
            "active": True,
            "closed": False,
            "volume": 850_000,
            "volume_24h": 42_000,
            "liquidity": 120_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.35, 0.65]",
            "start_date": "2024-11-01T00:00:00Z",
            "end_date": "2025-01-31T00:00:00Z",
        },
        {
            "id": "mock-btc-100k",
            "condition_id": "0xcdef1234567890abcdef1234567890abcdef1234",
            "question": "Will Bitcoin reach $100,000 before 2025?",
            "slug": "bitcoin-100k-2024",
            "description": "Resolves Yes if Bitcoin price reaches or exceeds $100,000 USD on any major exchange before January 1, 2025.",
            "category": "Crypto",
            "tags": ["crypto", "bitcoin", "price-prediction"],
            "active": True,
            "closed": False,
            "volume": 2_100_000,
            "volume_24h": 125_000,
            "liquidity": 380_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.72, 0.28]",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2025-01-01T00:00:00Z",
        },
        {
            "id": "mock-biden-approval",
            "condition_id": "0xef1234567890abcdef1234567890abcdef123456",
            "question": "Will Biden's approval rating exceed 45% in December 2024?",
            "slug": "biden-approval-december-2024",
            "description": "Based on 538 polling average.",
            "category": "Politics",
            "tags": ["politics", "approval-rating", "biden"],
            "active": True,
            "closed": False,
            "volume": 180_000,
            "volume_24h": 8_500,
            "liquidity": 25_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.22, 0.78]",
            "start_date": "2024-11-01T00:00:00Z",
            "end_date": "2024-12-31T00:00:00Z",
        },
        {
            "id": "mock-government-shutdown",
            "condition_id": "0x34567890abcdef1234567890abcdef1234567890",
            "question": "Will there be a government shutdown before February 2025?",
            "slug": "government-shutdown-jan-2025",
            "description": "Resolves Yes if the US federal government experiences a partial or full shutdown.",
            "category": "Politics",
            "tags": ["politics", "government", "budget"],
            "active": True,
            "closed": False,
            "volume": 520_000,
            "volume_24h": 28_000,
            "liquidity": 75_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.38, 0.62]",
            "start_date": "2024-12-01T00:00:00Z",
            "end_date": "2025-02-01T00:00:00Z",
        },
        {
            "id": "mock-eth-price",
            "condition_id": "0x7890abcdef1234567890abcdef1234567890abcd",
            "question": "Will Ethereum reach $5,000 before 2025?",
            "slug": "ethereum-5000-2024",
            "description": "Resolves Yes if ETH price reaches $5,000 on major exchanges.",
            "category": "Crypto",
            "tags": ["crypto", "ethereum", "price-prediction"],
            "active": True,
            "closed": False,
            "volume": 680_000,
            "volume_24h": 35_000,
            "liquidity": 95_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.45, 0.55]",
            "start_date": "2024-01-01T00:00:00Z",
            "end_date": "2025-01-01T00:00:00Z",
        },
        # Lower volume markets for testing tier classification
        {
            "id": "mock-oscars-best-picture",
            "condition_id": "0xabcd1234567890abcdef1234567890abcdef5678",
            "question": "Which film will win Best Picture at 2025 Oscars?",
            "slug": "oscars-best-picture-2025",
            "category": "Entertainment",
            "tags": ["entertainment", "oscars", "movies"],
            "active": True,
            "closed": False,
            "volume": 45_000,
            "volume_24h": 2_200,
            "liquidity": 8_000,
            "outcomes": ["Anora", "The Brutalist", "Conclave", "Other"],
            "outcome_prices": "[0.35, 0.25, 0.20, 0.20]",
            "start_date": "2024-12-01T00:00:00Z",
            "end_date": "2025-03-02T00:00:00Z",
        },
        {
            "id": "mock-nfl-mvp",
            "condition_id": "0x5678abcd1234567890abcdef1234567890abcdef",
            "question": "Who will win NFL MVP 2024 season?",
            "slug": "nfl-mvp-2024",
            "category": "Sports",
            "tags": ["sports", "nfl", "football"],
            "active": True,
            "closed": False,
            "volume": 8_500,
            "volume_24h": 450,
            "liquidity": 1_200,
            "outcomes": ["Josh Allen", "Lamar Jackson", "Joe Burrow", "Other"],
            "outcome_prices": "[0.40, 0.30, 0.15, 0.15]",
            "start_date": "2024-09-01T00:00:00Z",
            "end_date": "2025-02-08T00:00:00Z",
        },
    ]

    def __init__(self):
        self._markets = {m["id"]: m for m in self.MOCK_MARKETS}
        self._price_drift = {}  # Track price drift for realistic movement

    async def health_check(self) -> bool:
        """Mock always returns healthy."""
        return True

    async def fetch(self, **kwargs) -> list[Market]:
        """Fetch mock markets."""
        return await self.get_markets(**kwargs)

    async def get_markets(
        self,
        active: Optional[bool] = True,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Market]:
        """Return mock markets with realistic price movements."""
        markets = []

        for market_data in list(self._markets.values())[offset : offset + limit]:
            # Apply small random price drift for realism
            market_id = market_data["id"]
            if market_id not in self._price_drift:
                self._price_drift[market_id] = 0

            # Random walk price drift (-2% to +2%)
            self._price_drift[market_id] += random.uniform(-0.02, 0.02)
            self._price_drift[market_id] = max(-0.15, min(0.15, self._price_drift[market_id]))

            # Create market with drifted price
            data = market_data.copy()
            if data.get("outcome_prices"):
                prices = json.loads(data["outcome_prices"])
                base_price = prices[0]
                new_price = max(0.01, min(0.99, base_price + self._price_drift[market_id]))
                prices[0] = round(new_price, 2)
                prices[1] = round(1 - new_price, 2)
                data["outcome_prices"] = json.dumps(prices)

            # Add timestamps
            data["created_at"] = datetime.utcnow() - timedelta(days=random.randint(30, 180))
            data["updated_at"] = datetime.utcnow()

            market = Market(**data)
            markets.append(market.with_computed_fields())

        # Filter by active status
        if active is not None:
            markets = [m for m in markets if m.active == active]

        return markets

    async def get_market(self, market_id: str) -> Optional[Market]:
        """Get a single mock market."""
        if market_id not in self._markets:
            return None

        markets = await self.get_markets()
        for market in markets:
            if market.id == market_id:
                return market
        return None

    def add_mock_market(self, market_data: dict) -> None:
        """Add a custom mock market for testing."""
        self._markets[market_data["id"]] = market_data

    def set_market_price(self, market_id: str, price: float) -> None:
        """Set a specific price for testing signal generation."""
        if market_id in self._markets:
            market = self._markets[market_id]
            prices = [round(price, 2), round(1 - price, 2)]
            market["outcome_prices"] = json.dumps(prices)
