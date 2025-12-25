"""Data source services - abstractions over external APIs with mock support."""

from src.services.data_sources.base import DataSourceBase
from src.services.data_sources.polymarket import PolymarketDataSource, MockPolymarketDataSource
from src.services.data_sources.news import NewsDataSource, MockNewsDataSource
from src.services.data_sources.social import SocialDataSource, MockSocialDataSource

__all__ = [
    "DataSourceBase",
    "PolymarketDataSource",
    "MockPolymarketDataSource",
    "NewsDataSource",
    "MockNewsDataSource",
    "SocialDataSource",
    "MockSocialDataSource",
]
