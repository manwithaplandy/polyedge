"""Application configuration using environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = "development"
    debug: bool = True

    # Supabase
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    # AWS SES (for email alerts)
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    ses_sender_email: str = "alerts@polyedge.io"

    # External APIs (empty = use mocks)
    polymarket_api_url: str = "https://gamma-api.polymarket.com"
    newsapi_key: str = ""
    twitter_bearer_token: str = ""

    # Feature flags
    use_mock_data: bool = True  # Use mocks for development

    # Signal generation thresholds
    sentiment_divergence_threshold: float = 0.20
    volume_surge_multiplier: float = 3.0
    social_spike_multiplier: float = 5.0
    price_momentum_threshold: float = 0.10

    # Signal scan configuration (manual trigger only - no auto-scheduler for POC)
    signal_min_confidence: float = 0.5

    # Watchlist - comma-separated market slugs
    # Example: SIGNAL_WATCHLIST=us-recession-in-2025,russia-x-ukraine-ceasefire-in-2025
    signal_watchlist: str = ""

    # Discovery settings (find additional high-volume markets)
    signal_discovery_enabled: bool = False
    signal_discovery_max_markets: int = 5
    signal_discovery_min_volume: float = 1_000_000

    # Rate limit handling
    skip_news_api: bool = False  # Set True to disable NewsAPI calls
    skip_social_api: bool = True  # Twitter API expensive, disabled by default
    api_retry_after_minutes: int = 15  # Backoff time after rate limit

    # Tracking configuration
    tracking_enabled: bool = True  # Enable background tracking of signal performance
    tracking_interval_minutes: int = 60  # How often to run tracking updates
    tracking_expire_days: int = 30  # Days before ACTIVE signals are marked EXPIRED

    # Signal quality filters - prevent low-quality signals
    min_days_to_expiry: int = 7  # Skip markets expiring sooner than this
    min_market_tier: str = "LOW"  # Skip markets below this tier (THIN, LOW, MEDIUM, HIGH)
    min_price_for_signals: float = 0.05  # Skip markets with price below this (5%)
    max_price_for_signals: float = 0.95  # Skip markets with price above this (95%)

    # Sentiment divergence rule improvements
    min_sentiment_strength: float = 0.3  # Require |sentiment| > this value
    min_article_count: int = 5  # Require at least this many articles

    @property
    def watchlist(self) -> list[str]:
        """Parse watchlist from comma-separated string."""
        if not self.signal_watchlist:
            return []
        return [slug.strip() for slug in self.signal_watchlist.split(",") if slug.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
