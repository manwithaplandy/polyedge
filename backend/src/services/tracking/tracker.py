"""Signal performance tracking service."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from src.db.client import SupabaseClient
from src.models.signal import Signal, SignalStatus
from src.models.market import Market
from src.services.data_sources.polymarket import (
    PolymarketDataSource,
    MockPolymarketDataSource,
    is_market_current,
)

logger = logging.getLogger(__name__)


class SignalTracker:
    """
    Tracks signal performance over time.

    Responsibilities:
    - Update price tracking fields (price_1h, price_24h, price_7d)
    - Calculate gain percentages
    - Resolve signals when markets close
    - Generate performance statistics
    """

    def __init__(
        self,
        db_client: SupabaseClient,
        market_source: Optional[PolymarketDataSource] = None,
    ):
        self.db = db_client
        self.market_source = market_source or MockPolymarketDataSource()

    async def update_signal_tracking(self, signal: Signal) -> Signal:
        """
        Update a signal's tracking fields based on current market price.

        Called periodically (e.g., hourly) to track performance.
        """
        # Get current market data
        market = await self.market_source.get_market(signal.market_id)
        if not market or market.current_price is None:
            logger.warning(f"Could not get market data for signal {signal.id}")
            return signal

        # Validate market is still current and tradeable
        # Skip tracking updates for closed/archived markets unless they need resolution
        if not is_market_current(market):
            # Only process market close/resolution
            if market.closed and signal.status == SignalStatus.ACTIVE:
                await self._resolve_signal(signal, market)
                await self.db.update_signal(signal)
                logger.info(f"Resolved signal {signal.id} for closed market {signal.market_id}")
            else:
                logger.debug(f"Skipping update for signal {signal.id} - market {signal.market_id} is no longer current")
            return signal

        current_price = market.current_price
        now = datetime.now(timezone.utc)
        # Handle timezone-naive created_at from older signals
        created_at = signal.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        hours_since_signal = (now - created_at).total_seconds() / 3600

        # Update tracking based on time elapsed
        updated = False

        if hours_since_signal >= 1 and signal.price_1h is None:
            signal.price_1h = current_price
            signal.gain_1h_pct = signal.calculate_gain(current_price)
            updated = True
            logger.info(f"Signal {signal.id}: 1h price={current_price:.3f}, gain={signal.gain_1h_pct:+.2f}%")

        if hours_since_signal >= 24 and signal.price_24h is None:
            signal.price_24h = current_price
            signal.gain_24h_pct = signal.calculate_gain(current_price)
            updated = True
            logger.info(f"Signal {signal.id}: 24h price={current_price:.3f}, gain={signal.gain_24h_pct:+.2f}%")

        if hours_since_signal >= 168 and signal.price_7d is None:  # 7 days
            signal.price_7d = current_price
            signal.gain_7d_pct = signal.calculate_gain(current_price)
            updated = True
            logger.info(f"Signal {signal.id}: 7d price={current_price:.3f}, gain={signal.gain_7d_pct:+.2f}%")

        # Check if market has closed/resolved
        if market.closed and signal.status == SignalStatus.ACTIVE:
            await self._resolve_signal(signal, market)
            updated = True

        # Persist updates
        if updated:
            await self.db.update_signal(signal)

        return signal

    async def _resolve_signal(self, signal: Signal, market: Market) -> None:
        """Resolve a signal when the market closes."""
        final_price = market.current_price
        if final_price is None:
            logger.warning(f"Cannot resolve signal {signal.id}: no final price available")
            return

        gain = signal.calculate_gain(final_price)

        # Determine win/loss based on gain percentage
        # A positive gain means the prediction was correct
        is_win = gain > 0

        signal.price_at_resolution = final_price
        signal.gain_final_pct = gain
        signal.status = SignalStatus.RESOLVED_WIN if is_win else SignalStatus.RESOLVED_LOSS
        signal.resolved_at = datetime.now(timezone.utc)

        logger.info(
            f"Signal {signal.id} RESOLVED: {signal.status.value} "
            f"(entry={signal.entry_price:.3f}, exit={final_price:.3f}, gain={gain:+.2f}%)"
        )

    async def update_all_active_signals(self) -> int:
        """
        Update tracking for all active signals.

        Returns number of signals updated.
        """
        active_signals = await self.db.get_active_signals()
        updated_count = 0

        for signal in active_signals:
            try:
                await self.update_signal_tracking(signal)
                updated_count += 1
            except Exception as e:
                logger.error(f"Error updating signal {signal.id}: {e}")

        logger.info(f"Updated tracking for {updated_count}/{len(active_signals)} active signals")
        return updated_count

    async def expire_stale_signals(self, max_age_days: int = 30) -> int:
        """
        Mark very old active signals as expired.

        Returns number of signals expired.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        active_signals = await self.db.get_active_signals()

        expired_count = 0
        for signal in active_signals:
            # Handle timezone-naive created_at from older signals
            created_at = signal.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)
            if created_at < cutoff:
                signal.status = SignalStatus.EXPIRED
                signal.resolved_at = datetime.now(timezone.utc)
                await self.db.update_signal(signal)
                expired_count += 1
                logger.info(f"Expired stale signal {signal.id}")

        return expired_count

    async def get_performance_summary(self) -> dict:
        """Get summary of signal performance."""
        stats = await self.db.get_signal_stats()
        stats_by_type = await self.db.get_signal_stats_by_type()

        return {
            "overall": {
                "total_signals": stats.total_signals,
                "active_signals": stats.active_signals,
                "resolved_signals": stats.resolved_signals,
                "wins": stats.wins,
                "losses": stats.losses,
                "win_rate": stats.win_rate,
                "avg_gain_pct": stats.avg_gain_pct,
                "best_gain_pct": stats.best_gain_pct,
                "worst_gain_pct": stats.worst_gain_pct,
            },
            "by_type": stats_by_type,
        }
