"""Signal API endpoints."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.config import get_settings
from src.models.signal import Signal, SignalStatus, SignalType, SignalStats
from src.db.client import get_supabase_client
from src.services.data_sources.polymarket import MockPolymarketDataSource, PolymarketDataSource
from src.services.data_sources.news import MockNewsDataSource, NewsDataSource
from src.services.data_sources.social import MockSocialDataSource, SocialDataSource
from src.services.signals.generator import SignalGenerator, MockSignalGenerator
from src.services.signals.scanner import get_scanner

router = APIRouter()


class SignalResponse(BaseModel):
    """API response for a single signal."""

    id: str
    created_at: str
    market_id: str
    market_question: str
    market_slug: Optional[str]
    signal_type: str
    direction: str
    confidence: float
    reasoning: str
    entry_price: float
    market_tier: str
    status: str
    # Current performance
    current_gain_pct: Optional[float] = None
    # Tracking data
    gain_1h_pct: Optional[float] = None
    gain_24h_pct: Optional[float] = None
    gain_7d_pct: Optional[float] = None
    gain_final_pct: Optional[float] = None

    @classmethod
    def from_signal(cls, signal: Signal, current_price: Optional[float] = None) -> "SignalResponse":
        current_gain = None
        if current_price is not None:
            current_gain = signal.calculate_gain(current_price)

        return cls(
            id=str(signal.id),
            created_at=signal.created_at.isoformat(),
            market_id=signal.market_id,
            market_question=signal.market_question,
            market_slug=signal.market_slug,
            signal_type=signal.signal_type.value,
            direction=signal.direction.value,
            confidence=signal.confidence,
            reasoning=signal.reasoning,
            entry_price=signal.entry_price,
            market_tier=signal.market_tier.value,
            status=signal.status.value,
            current_gain_pct=round(current_gain, 2) if current_gain else None,
            gain_1h_pct=signal.gain_1h_pct,
            gain_24h_pct=signal.gain_24h_pct,
            gain_7d_pct=signal.gain_7d_pct,
            gain_final_pct=signal.gain_final_pct,
        )


class SignalListResponse(BaseModel):
    """API response for list of signals."""

    signals: list[SignalResponse]
    total: int
    offset: int
    limit: int


@router.get("", response_model=SignalListResponse)
async def list_signals(
    status: Optional[str] = Query(None, description="Filter by status (ACTIVE, RESOLVED_WIN, etc.)"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List signals with optional filters."""
    settings = get_settings()

    # In mock mode, generate some signals on the fly
    if settings.use_mock_data:
        signals = await _generate_mock_signals()
    else:
        db = get_supabase_client()
        status_filter = SignalStatus(status) if status else None
        signals = await db.get_signals(
            status=status_filter,
            signal_type=signal_type,
            limit=limit,
            offset=offset,
        )

    # Convert to response models
    signal_responses = [SignalResponse.from_signal(s) for s in signals]

    return SignalListResponse(
        signals=signal_responses[offset : offset + limit],
        total=len(signal_responses),
        offset=offset,
        limit=limit,
    )


@router.get("/active", response_model=SignalListResponse)
async def get_active_signals():
    """Get all currently active signals."""
    settings = get_settings()

    if settings.use_mock_data:
        signals = await _generate_mock_signals()
        active = [s for s in signals if s.status == SignalStatus.ACTIVE]
    else:
        db = get_supabase_client()
        active = await db.get_active_signals()

    return SignalListResponse(
        signals=[SignalResponse.from_signal(s) for s in active],
        total=len(active),
        offset=0,
        limit=len(active),
    )


@router.get("/stats", response_model=SignalStats)
async def get_signal_stats():
    """Get aggregate signal performance statistics."""
    settings = get_settings()

    if settings.use_mock_data:
        # Return mock stats
        return SignalStats(
            total_signals=142,
            active_signals=5,
            resolved_signals=137,
            wins=93,
            losses=44,
            win_rate=67.9,
            avg_gain_pct=9.2,
            best_gain_pct=34.5,
            worst_gain_pct=-18.3,
            stats_by_type={
                "SENTIMENT_DIVERGENCE": {"total": 45, "wins": 32, "losses": 13, "win_rate": 71.1, "avg_gain": 11.2},
                "VOLUME_SURGE": {"total": 38, "wins": 26, "losses": 12, "win_rate": 68.4, "avg_gain": 8.4},
                "SOCIAL_SPIKE": {"total": 31, "wins": 19, "losses": 12, "win_rate": 61.3, "avg_gain": 6.1},
                "PRICE_MOMENTUM": {"total": 28, "wins": 16, "losses": 12, "win_rate": 57.1, "avg_gain": 7.8},
            },
        )
    else:
        db = get_supabase_client()
        stats = await db.get_signal_stats()
        stats.stats_by_type = await db.get_signal_stats_by_type()
        return stats


@router.get("/{signal_id}", response_model=SignalResponse)
async def get_signal(signal_id: str):
    """Get a single signal by ID."""
    settings = get_settings()

    if settings.use_mock_data:
        signals = await _generate_mock_signals()
        for s in signals:
            if str(s.id) == signal_id:
                return SignalResponse.from_signal(s)
        raise HTTPException(status_code=404, detail="Signal not found")
    else:
        db = get_supabase_client()
        signal = await db.get_signal(UUID(signal_id))
        if not signal:
            raise HTTPException(status_code=404, detail="Signal not found")
        return SignalResponse.from_signal(signal)


async def _generate_mock_signals() -> list[Signal]:
    """Generate mock signals for development."""
    # Get mock market data
    market_source = MockPolymarketDataSource()
    news_source = MockNewsDataSource()
    social_source = MockSocialDataSource()

    markets = await market_source.get_markets(limit=10)

    # Use mock generator with seeded previous states
    generator = MockSignalGenerator(min_confidence=0.4)

    all_signals = []
    for market in markets[:5]:  # Limit to first 5 markets
        # Get context
        query = market.question.split()[0]  # Use first word as search term
        news_sentiment = await news_source.get_sentiment_for_market(market.id, query)
        social_mentions = await social_source.get_mentions_for_market(market.id, query)
        social_sentiment = await social_source.get_sentiment_for_market(market.id, query)

        # Generate signals (don't persist)
        signals = await generator.process_market(
            market=market,
            news_sentiment=news_sentiment,
            social_mentions=social_mentions,
            social_sentiment=social_sentiment,
            persist=False,
        )
        all_signals.extend(signals)

    return all_signals


# ============================================
# SCAN ENDPOINTS
# ============================================


class ScanResponse(BaseModel):
    """Response from a signal scan."""

    signals_generated: int
    markets_scanned: int
    signals: list[SignalResponse]
    degraded: dict
    errors: list[str]
    scan_time: str


class ScanStatusResponse(BaseModel):
    """Status of the signal scanner."""

    watchlist: list[str]
    discovery_enabled: bool
    min_confidence: float
    apis: dict
    last_scan: Optional[str]
    last_scan_signals: int


@router.post("/scan", response_model=ScanResponse)
async def trigger_scan(
    markets: Optional[str] = Query(
        None,
        description="Comma-separated list of market slugs to scan (overrides watchlist)",
    ),
    persist: bool = Query(True, description="Whether to persist generated signals to database"),
):
    """
    Trigger a manual signal scan.

    Scans the configured watchlist (or override markets) for trading signals.
    Returns generated signals and any degradation status.
    """
    scanner = get_scanner()

    # Parse override markets if provided
    override_slugs = None
    if markets:
        override_slugs = [slug.strip() for slug in markets.split(",") if slug.strip()]

    # Run the scan
    result = await scanner.run_scan(
        override_markets=override_slugs,
        persist=persist,
    )

    # Convert signals to response format
    signal_responses = [SignalResponse.from_signal(s) for s in result.signals]

    return ScanResponse(
        signals_generated=result.signals_generated,
        markets_scanned=result.markets_scanned,
        signals=signal_responses,
        degraded=result.degraded,
        errors=result.errors,
        scan_time=result.scan_time.isoformat(),
    )


@router.get("/scan/status", response_model=ScanStatusResponse)
async def get_scan_status():
    """
    Get the current status of the signal scanner.

    Returns watchlist configuration, API availability, and last scan info.
    """
    scanner = get_scanner()
    status = scanner.get_status()

    return ScanStatusResponse(
        watchlist=status["watchlist"],
        discovery_enabled=status["discovery_enabled"],
        min_confidence=status["min_confidence"],
        apis=status["apis"],
        last_scan=status["last_scan"],
        last_scan_signals=status["last_scan_signals"],
    )
