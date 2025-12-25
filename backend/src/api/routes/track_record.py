"""Track record API endpoints - the key marketing feature."""

from typing import Optional
from datetime import datetime, timedelta
import csv
import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.config import get_settings
from src.models.signal import SignalStatus

router = APIRouter()


class TrackRecordSummary(BaseModel):
    """Overall track record summary."""

    total_signals: int
    active_signals: int
    resolved_signals: int
    wins: int
    losses: int
    win_rate_pct: float
    avg_gain_pct: float
    best_gain_pct: float
    worst_gain_pct: float
    # Theoretical returns
    theoretical_return_1k: float  # If you put $1K on each signal


class SignalTypeStats(BaseModel):
    """Stats for a single signal type."""

    signal_type: str
    total_signals: int
    wins: int
    losses: int
    win_rate_pct: float
    avg_gain_pct: float
    best_gain_pct: float


class TrackRecordResponse(BaseModel):
    """Full track record response."""

    summary: TrackRecordSummary
    by_signal_type: list[SignalTypeStats]
    last_updated: str


class SignalHistoryItem(BaseModel):
    """Single item in signal history."""

    id: str
    date: str
    market_question: str
    signal_type: str
    direction: str
    confidence: float
    entry_price: float
    exit_price: Optional[float]
    gain_pct: Optional[float]
    status: str


class SignalHistoryResponse(BaseModel):
    """Paginated signal history."""

    signals: list[SignalHistoryItem]
    total: int
    offset: int
    limit: int


@router.get("", response_model=TrackRecordResponse)
async def get_track_record():
    """
    Get the full track record - this is the key marketing feature.

    Shows aggregate performance across all signals.
    """
    settings = get_settings()

    if settings.use_mock_data:
        # Return compelling mock data
        return TrackRecordResponse(
            summary=TrackRecordSummary(
                total_signals=142,
                active_signals=5,
                resolved_signals=137,
                wins=93,
                losses=44,
                win_rate_pct=67.9,
                avg_gain_pct=9.2,
                best_gain_pct=34.5,
                worst_gain_pct=-18.3,
                theoretical_return_1k=12_604.0,  # $1K * 137 signals * 9.2% avg = $12.6K profit
            ),
            by_signal_type=[
                SignalTypeStats(
                    signal_type="SENTIMENT_DIVERGENCE",
                    total_signals=45,
                    wins=32,
                    losses=13,
                    win_rate_pct=71.1,
                    avg_gain_pct=11.2,
                    best_gain_pct=34.5,
                ),
                SignalTypeStats(
                    signal_type="VOLUME_SURGE",
                    total_signals=38,
                    wins=26,
                    losses=12,
                    win_rate_pct=68.4,
                    avg_gain_pct=8.4,
                    best_gain_pct=28.1,
                ),
                SignalTypeStats(
                    signal_type="SOCIAL_SPIKE",
                    total_signals=31,
                    wins=19,
                    losses=12,
                    win_rate_pct=61.3,
                    avg_gain_pct=6.1,
                    best_gain_pct=19.2,
                ),
                SignalTypeStats(
                    signal_type="PRICE_MOMENTUM",
                    total_signals=28,
                    wins=16,
                    losses=12,
                    win_rate_pct=57.1,
                    avg_gain_pct=7.8,
                    best_gain_pct=22.4,
                ),
            ],
            last_updated=datetime.utcnow().isoformat(),
        )
    else:
        # Get from database
        from src.db.client import get_supabase_client
        from src.services.tracking.tracker import SignalTracker

        db = get_supabase_client()
        stats = await db.get_signal_stats()
        stats_by_type = await db.get_signal_stats_by_type()

        # Calculate theoretical return
        theoretical_return = stats.resolved_signals * 1000 * (stats.avg_gain_pct / 100)

        return TrackRecordResponse(
            summary=TrackRecordSummary(
                total_signals=stats.total_signals,
                active_signals=stats.active_signals,
                resolved_signals=stats.resolved_signals,
                wins=stats.wins,
                losses=stats.losses,
                win_rate_pct=stats.win_rate,
                avg_gain_pct=stats.avg_gain_pct,
                best_gain_pct=stats.best_gain_pct,
                worst_gain_pct=stats.worst_gain_pct,
                theoretical_return_1k=theoretical_return,
            ),
            by_signal_type=[
                SignalTypeStats(
                    signal_type=signal_type,
                    total_signals=data.get("total_signals", 0),
                    wins=data.get("wins", 0),
                    losses=data.get("losses", 0),
                    win_rate_pct=data.get("win_rate", 0),
                    avg_gain_pct=data.get("avg_gain_pct", 0),
                    best_gain_pct=data.get("best_gain_pct", 0),
                )
                for signal_type, data in stats_by_type.items()
            ],
            last_updated=datetime.utcnow().isoformat(),
        )


@router.get("/history", response_model=SignalHistoryResponse)
async def get_signal_history(
    status: Optional[str] = Query(None, description="Filter by status"),
    signal_type: Optional[str] = Query(None, description="Filter by signal type"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Get paginated signal history for the track record page."""
    settings = get_settings()

    if settings.use_mock_data:
        # Generate mock history
        history = _generate_mock_history()

        # Apply filters
        if status:
            history = [h for h in history if h.status == status]
        if signal_type:
            history = [h for h in history if h.signal_type == signal_type]

        # Paginate
        total = len(history)
        paginated = history[offset : offset + limit]

        return SignalHistoryResponse(
            signals=paginated,
            total=total,
            offset=offset,
            limit=limit,
        )
    else:
        from src.db.client import get_supabase_client

        db = get_supabase_client()
        status_filter = SignalStatus(status) if status else None
        signals = await db.get_signals(
            status=status_filter,
            signal_type=signal_type,
            limit=limit,
            offset=offset,
        )

        return SignalHistoryResponse(
            signals=[
                SignalHistoryItem(
                    id=str(s.id),
                    date=s.created_at.strftime("%Y-%m-%d"),
                    market_question=s.market_question[:60] + "..." if len(s.market_question) > 60 else s.market_question,
                    signal_type=s.signal_type.value,
                    direction=s.direction.value,
                    confidence=s.confidence,
                    entry_price=s.entry_price,
                    exit_price=s.price_at_resolution,
                    gain_pct=s.gain_final_pct,
                    status=s.status.value,
                )
                for s in signals
            ],
            total=len(signals),  # This should be total count, but simplified for now
            offset=offset,
            limit=limit,
        )


@router.get("/export")
async def export_track_record():
    """Export full track record as CSV."""
    settings = get_settings()

    if settings.use_mock_data:
        history = _generate_mock_history()
    else:
        from src.db.client import get_supabase_client

        db = get_supabase_client()
        signals = await db.get_signals(limit=1000)
        history = [
            SignalHistoryItem(
                id=str(s.id),
                date=s.created_at.strftime("%Y-%m-%d"),
                market_question=s.market_question,
                signal_type=s.signal_type.value,
                direction=s.direction.value,
                confidence=s.confidence,
                entry_price=s.entry_price,
                exit_price=s.price_at_resolution,
                gain_pct=s.gain_final_pct,
                status=s.status.value,
            )
            for s in signals
        ]

    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Date", "Market", "Signal Type", "Direction",
        "Confidence", "Entry Price", "Exit Price", "Gain %", "Status"
    ])

    for item in history:
        writer.writerow([
            item.id,
            item.date,
            item.market_question,
            item.signal_type,
            item.direction,
            item.confidence,
            item.entry_price,
            item.exit_price or "",
            f"{item.gain_pct:.2f}" if item.gain_pct else "",
            item.status,
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=polyedge_track_record.csv"},
    )


def _generate_mock_history() -> list[SignalHistoryItem]:
    """Generate mock signal history for demo."""
    import random

    markets = [
        "Will Trump win the 2024 election?",
        "Will Harris win the 2024 election?",
        "Will Bitcoin reach $100K in 2024?",
        "Will the Fed cut rates in January 2025?",
        "Will Republicans control the Senate?",
        "Will there be a government shutdown?",
        "Will Ethereum reach $5,000?",
        "Will Biden's approval exceed 45%?",
    ]

    signal_types = ["SENTIMENT_DIVERGENCE", "VOLUME_SURGE", "SOCIAL_SPIKE", "PRICE_MOMENTUM"]

    history = []
    base_date = datetime.utcnow()

    for i in range(100):
        is_win = random.random() < 0.68  # 68% win rate
        signal_type = random.choice(signal_types)
        direction = random.choice(["BUY", "SELL"])
        entry_price = round(random.uniform(0.2, 0.8), 2)

        if is_win:
            if direction == "BUY":
                exit_price = round(entry_price + random.uniform(0.03, 0.15), 2)
            else:
                exit_price = round(entry_price - random.uniform(0.03, 0.15), 2)
            gain = round((exit_price - entry_price) / entry_price * 100, 2)
            if direction == "SELL":
                gain = -gain
            status = "RESOLVED_WIN"
        else:
            if direction == "BUY":
                exit_price = round(entry_price - random.uniform(0.02, 0.10), 2)
            else:
                exit_price = round(entry_price + random.uniform(0.02, 0.10), 2)
            gain = round((exit_price - entry_price) / entry_price * 100, 2)
            if direction == "SELL":
                gain = -gain
            status = "RESOLVED_LOSS"

        # Clamp prices
        exit_price = max(0.01, min(0.99, exit_price))

        date = base_date - timedelta(days=i)

        history.append(
            SignalHistoryItem(
                id=f"mock-signal-{i:04d}",
                date=date.strftime("%Y-%m-%d"),
                market_question=random.choice(markets),
                signal_type=signal_type,
                direction=direction,
                confidence=round(random.uniform(0.5, 0.95), 2),
                entry_price=entry_price,
                exit_price=exit_price,
                gain_pct=gain,
                status=status,
            )
        )

    return history
