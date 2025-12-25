"""Market models matching Polymarket Gamma API structure."""

import json
from datetime import datetime
from enum import Enum
from typing import Optional, Union
from pydantic import BaseModel, Field, field_validator


class MarketTier(str, Enum):
    """Market health tier based on volume quartiles."""

    THIN = "THIN"  # < $10K volume
    LOW = "LOW"  # $10K - $27K volume
    MEDIUM = "MEDIUM"  # $27K - $95K volume
    HIGH = "HIGH"  # > $95K volume


class MarketOutcome(BaseModel):
    """Individual outcome within a market."""

    outcome: str
    outcome_prices: Optional[str] = None  # JSON string of price
    price: Optional[float] = None


class Market(BaseModel):
    """
    Market model matching Polymarket Gamma API structure.

    Based on: https://gamma-api.polymarket.com/markets
    """

    # Core identifiers
    id: str = Field(description="Unique market ID")
    condition_id: str = Field(alias="conditionId", description="Condition ID for CLOB operations")
    question: str = Field(description="Market question text")
    slug: Optional[str] = Field(default=None, description="URL slug")

    # Description and metadata
    description: Optional[str] = Field(default=None)
    category: Optional[str] = Field(default=None)
    tags: list[str] = Field(default_factory=list)

    # Market state
    active: bool = Field(default=True)
    closed: bool = Field(default=False)
    archived: bool = Field(default=False)
    accepting_orders: bool = Field(default=True)

    # Timestamps
    start_date: Optional[datetime] = Field(default=None)
    end_date: Optional[datetime] = Field(default=None)
    created_at: Optional[datetime] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)

    # Trading data
    volume: float = Field(default=0.0, description="Total volume in USD")
    volume_24h: float = Field(default=0.0, alias="volume24hr", description="24h volume in USD")
    liquidity: float = Field(default=0.0, description="Current liquidity")

    # Outcomes and pricing
    outcomes: list[str] = Field(default_factory=list, description="Possible outcomes")
    outcome_prices: Optional[str] = Field(default=None, alias="outcomePrices", description="JSON prices")

    # Token IDs for trading
    clob_token_ids: Optional[str] = Field(default=None, alias="clobTokenIds", description="JSON token IDs")

    @field_validator("outcomes", mode="before")
    @classmethod
    def parse_outcomes(cls, v: Union[str, list]) -> list[str]:
        """Parse outcomes from JSON string if needed."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v or []

    # Resolution
    resolution_source: Optional[str] = Field(default=None)
    resolved_by: Optional[str] = Field(default=None)

    # Computed fields (not from API)
    tier: Optional[MarketTier] = Field(default=None, description="Computed volume tier")
    current_price: Optional[float] = Field(default=None, description="Primary outcome price")

    class Config:
        populate_by_name = True

    def compute_tier(self) -> MarketTier:
        """Compute market tier based on volume thresholds."""
        if self.volume < 10_000:
            return MarketTier.THIN
        elif self.volume < 27_000:
            return MarketTier.LOW
        elif self.volume < 95_000:
            return MarketTier.MEDIUM
        else:
            return MarketTier.HIGH

    def with_computed_fields(self) -> "Market":
        """Return market with computed fields populated."""
        self.tier = self.compute_tier()
        # Parse current price from outcome_prices if available
        if self.outcome_prices:
            try:
                prices = json.loads(self.outcome_prices)
                if prices and len(prices) > 0:
                    self.current_price = float(prices[0])
            except (json.JSONDecodeError, ValueError, IndexError):
                pass
        return self


class MarketSnapshot(BaseModel):
    """Point-in-time snapshot of market state for signal generation."""

    market_id: str
    timestamp: datetime
    price: float
    volume_24h: float
    volume_total: float
    liquidity: float
    tier: MarketTier
