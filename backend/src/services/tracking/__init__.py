"""Signal tracking and outcome monitoring services."""

from datetime import datetime
from typing import Optional

from src.config import get_settings
from src.db.client import get_supabase_client
from src.services.data_sources.polymarket import PolymarketDataSource, MockPolymarketDataSource
from src.services.tracking.tracker import SignalTracker

__all__ = ["SignalTracker", "get_tracker"]


# Global tracker instance
_tracker: Optional[SignalTracker] = None
_last_tracking_run: Optional[datetime] = None


def get_tracker() -> SignalTracker:
    """Get or create the global tracker instance."""
    global _tracker
    if _tracker is None:
        settings = get_settings()
        db = get_supabase_client()
        if settings.use_mock_data:
            market_source = MockPolymarketDataSource()
        else:
            market_source = PolymarketDataSource()
        _tracker = SignalTracker(db, market_source)
    return _tracker


def get_last_tracking_run() -> Optional[datetime]:
    """Get the timestamp of the last tracking run."""
    return _last_tracking_run


def set_last_tracking_run(timestamp: datetime) -> None:
    """Set the timestamp of the last tracking run."""
    global _last_tracking_run
    _last_tracking_run = timestamp
