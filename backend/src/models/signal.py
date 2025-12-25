"""Signal models for trade recommendations."""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4
from pydantic import BaseModel, Field

from src.models.market import MarketTier


class SignalType(str, Enum):
    """Type of signal that triggered the recommendation."""

    SENTIMENT_DIVERGENCE = "SENTIMENT_DIVERGENCE"
    VOLUME_SURGE = "VOLUME_SURGE"
    SOCIAL_SPIKE = "SOCIAL_SPIKE"
    PRICE_MOMENTUM = "PRICE_MOMENTUM"
    ARBITRAGE = "ARBITRAGE"


class SignalDirection(str, Enum):
    """Direction of the trade recommendation."""

    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(str, Enum):
    """Current status of the signal."""

    ACTIVE = "ACTIVE"
    RESOLVED_WIN = "RESOLVED_WIN"
    RESOLVED_LOSS = "RESOLVED_LOSS"
    EXPIRED = "EXPIRED"


class Signal(BaseModel):
    """
    Trade signal with full context and performance tracking.

    This is the core model that powers the track record feature.
    Every signal is recorded with enough context to:
    1. Understand why it was generated
    2. Track its performance over time
    3. Calculate gain/loss when resolved
    """

    # Identification
    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Market context at signal time
    market_id: str
    market_question: str
    market_slug: Optional[str] = None
    market_end_date: Optional[datetime] = None

    # Signal details
    signal_type: SignalType
    direction: SignalDirection
    confidence: float = Field(ge=0.0, le=1.0, description="0.0 to 1.0 confidence score")
    reasoning: str = Field(description="Human-readable explanation of the signal")

    # Market state at signal time
    entry_price: float = Field(ge=0.0, le=1.0, description="Price when signal generated")
    entry_volume_24h: float = Field(default=0.0)
    entry_volume_total: float = Field(default=0.0)
    entry_liquidity: float = Field(default=0.0)
    market_tier: MarketTier

    # External context at signal time
    news_sentiment_score: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0, description="News sentiment -1.0 to 1.0"
    )
    social_mention_count_24h: Optional[int] = Field(default=None)
    social_sentiment_score: Optional[float] = Field(
        default=None, ge=-1.0, le=1.0, description="Social sentiment -1.0 to 1.0"
    )

    # Performance tracking (updated over time by tracking service)
    price_1h: Optional[float] = Field(default=None, description="Price 1 hour after signal")
    price_24h: Optional[float] = Field(default=None, description="Price 24 hours after signal")
    price_7d: Optional[float] = Field(default=None, description="Price 7 days after signal")
    price_at_resolution: Optional[float] = Field(default=None, description="Final price")

    # Calculated gains (computed from prices)
    gain_1h_pct: Optional[float] = Field(default=None)
    gain_24h_pct: Optional[float] = Field(default=None)
    gain_7d_pct: Optional[float] = Field(default=None)
    gain_final_pct: Optional[float] = Field(default=None)

    # Resolution
    status: SignalStatus = Field(default=SignalStatus.ACTIVE)
    resolved_at: Optional[datetime] = Field(default=None)

    def calculate_gain(self, current_price: float) -> float:
        """
        Calculate percentage gain based on direction and price change.

        For BUY signals: gain = (current - entry) / entry
        For SELL signals: gain = (entry - current) / entry
        """
        if self.direction == SignalDirection.BUY:
            return (current_price - self.entry_price) / self.entry_price * 100
        else:
            return (self.entry_price - current_price) / self.entry_price * 100

    def update_tracking(
        self,
        current_price: float,
        hours_since_signal: float,
    ) -> "Signal":
        """Update tracking fields based on current price and time elapsed."""
        gain = self.calculate_gain(current_price)

        if hours_since_signal >= 1 and self.price_1h is None:
            self.price_1h = current_price
            self.gain_1h_pct = gain
        elif hours_since_signal >= 24 and self.price_24h is None:
            self.price_24h = current_price
            self.gain_24h_pct = gain
        elif hours_since_signal >= 168 and self.price_7d is None:  # 7 days
            self.price_7d = current_price
            self.gain_7d_pct = gain

        return self

    def resolve(self, final_price: float, is_win: bool) -> "Signal":
        """Mark the signal as resolved with final outcome."""
        self.price_at_resolution = final_price
        self.gain_final_pct = self.calculate_gain(final_price)
        self.status = SignalStatus.RESOLVED_WIN if is_win else SignalStatus.RESOLVED_LOSS
        self.resolved_at = datetime.utcnow()
        return self


class SignalStats(BaseModel):
    """Aggregate statistics for signal performance."""

    total_signals: int = 0
    active_signals: int = 0
    resolved_signals: int = 0

    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0

    avg_gain_pct: float = 0.0
    best_gain_pct: float = 0.0
    worst_gain_pct: float = 0.0

    # By signal type
    stats_by_type: dict[str, dict] = Field(default_factory=dict)


class SignalCreate(BaseModel):
    """Input model for creating a new signal."""

    market_id: str
    signal_type: SignalType
    direction: SignalDirection
    confidence: float
    reasoning: str

    # Optional overrides (usually computed from market data)
    entry_price: Optional[float] = None
    news_sentiment_score: Optional[float] = None
    social_mention_count_24h: Optional[int] = None
    social_sentiment_score: Optional[float] = None
