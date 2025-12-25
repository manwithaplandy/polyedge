"""Market API endpoints."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.config import get_settings
from src.db.client import get_supabase_client
from src.models.market import Market, MarketTier
from src.models.signal import SignalStatus
from src.services.data_sources.polymarket import MockPolymarketDataSource, PolymarketDataSource

router = APIRouter()


class MarketResponse(BaseModel):
    """API response for a single market."""

    id: str
    condition_id: str
    question: str
    slug: Optional[str]
    description: Optional[str]
    category: Optional[str]
    active: bool
    closed: bool
    volume: float
    volume_24h: float
    liquidity: float
    current_price: Optional[float]
    tier: str
    outcomes: list[str]
    end_date: Optional[str]
    # Our analysis
    has_active_signal: bool = False

    @classmethod
    def from_market(cls, market: Market, has_signal: bool = False) -> "MarketResponse":
        return cls(
            id=market.id,
            condition_id=market.condition_id,
            question=market.question,
            slug=market.slug,
            description=market.description,
            category=market.category,
            active=market.active,
            closed=market.closed,
            volume=market.volume,
            volume_24h=market.volume_24h,
            liquidity=market.liquidity,
            current_price=market.current_price,
            tier=market.tier.value if market.tier else MarketTier.THIN.value,
            outcomes=market.outcomes,
            end_date=market.end_date.isoformat() if market.end_date else None,
            has_active_signal=has_signal,
        )


class MarketListResponse(BaseModel):
    """API response for list of markets."""

    markets: list[MarketResponse]
    total: int
    offset: int
    limit: int


@router.get("", response_model=MarketListResponse)
async def list_markets(
    tier: Optional[str] = Query(None, description="Filter by tier (THIN, LOW, MEDIUM, HIGH)"),
    active: Optional[bool] = Query(True, description="Filter by active status"),
    has_active_signal: Optional[bool] = Query(None, description="Filter to markets with active signals"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List markets with our analysis overlay."""
    settings = get_settings()

    if settings.use_mock_data:
        source = MockPolymarketDataSource()
    else:
        source = PolymarketDataSource()

    markets = await source.get_markets(
        active=active,
        limit=limit,
        offset=offset,
        filter_current=True,  # Explicitly filter closed/archived markets
    )

    # Filter by tier if specified
    if tier:
        tier_enum = MarketTier(tier)
        markets = [m for m in markets if m.tier == tier_enum]

    # Get markets with active signals
    markets_with_signals: set[str] = set()
    if has_active_signal is not None or True:  # Always fetch to show indicator
        try:
            db = get_supabase_client()
            active_signals = await db.get_active_signals()
            markets_with_signals = {s.market_id for s in active_signals if s.market_id}
        except Exception:
            # If DB unavailable, continue without signal data
            pass

    # Filter by has_active_signal if specified
    if has_active_signal is True:
        markets = [m for m in markets if m.id in markets_with_signals]
    elif has_active_signal is False:
        markets = [m for m in markets if m.id not in markets_with_signals]

    market_responses = [
        MarketResponse.from_market(m, has_signal=(m.id in markets_with_signals))
        for m in markets
    ]

    return MarketListResponse(
        markets=market_responses,
        total=len(market_responses),
        offset=offset,
        limit=limit,
    )


@router.get("/{market_id}", response_model=MarketResponse)
async def get_market(market_id: str):
    """Get a single market with our analysis."""
    settings = get_settings()

    if settings.use_mock_data:
        source = MockPolymarketDataSource()
    else:
        source = PolymarketDataSource()

    market = await source.get_market(market_id)
    if not market:
        raise HTTPException(status_code=404, detail="Market not found")

    return MarketResponse.from_market(market)


@router.get("/tier/{tier}", response_model=MarketListResponse)
async def get_markets_by_tier(
    tier: str,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get markets filtered by volume tier."""
    try:
        tier_enum = MarketTier(tier.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(t.value for t in MarketTier)}",
        )

    settings = get_settings()

    if settings.use_mock_data:
        source = MockPolymarketDataSource()
    else:
        source = PolymarketDataSource()

    markets = await source.get_markets(
        active=True,  # Only active markets
        limit=100,  # Get more to filter
        filter_current=True,  # Explicitly filter closed/archived markets
    )
    filtered = [m for m in markets if m.tier == tier_enum]

    # Apply pagination
    paginated = filtered[offset : offset + limit]

    return MarketListResponse(
        markets=[MarketResponse.from_market(m) for m in paginated],
        total=len(filtered),
        offset=offset,
        limit=limit,
    )
