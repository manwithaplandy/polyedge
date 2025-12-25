"""Configurable signal scanner for market analysis."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.config import get_settings, Settings
from src.db.client import get_supabase_client
from src.models.market import Market
from src.models.signal import Signal
from src.models.news import NewsSentiment
from src.models.social import SocialMention, SocialSentiment
from src.services.data_sources.polymarket import PolymarketDataSource, MockPolymarketDataSource
from src.services.data_sources.news import NewsDataSource, MockNewsDataSource
from src.services.data_sources.social import SocialDataSource, MockSocialDataSource
from src.services.data_sources.rate_limiter import get_rate_limiter, get_all_api_status
from src.services.signals.generator import SignalGenerator

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a signal scan."""

    signals_generated: int = 0
    markets_scanned: int = 0
    signals: list[Signal] = field(default_factory=list)
    degraded: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    scan_time: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        """Convert to dictionary for API response."""
        return {
            "signals_generated": self.signals_generated,
            "markets_scanned": self.markets_scanned,
            "signals": [s.model_dump(mode="json") for s in self.signals],
            "degraded": self.degraded,
            "errors": self.errors,
            "scan_time": self.scan_time.isoformat(),
        }


class SignalScanner:
    """
    Configurable market scanner for signal generation.

    Supports:
    - Watchlist of specific markets to monitor
    - Optional discovery of high-volume markets
    - Graceful degradation when APIs are rate-limited
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.generator = SignalGenerator(min_confidence=self.settings.signal_min_confidence)

        # Initialize data sources based on mock mode
        if self.settings.use_mock_data:
            self.polymarket = MockPolymarketDataSource()
            self.news = MockNewsDataSource()
            self.social = MockSocialDataSource()
        else:
            self.polymarket = PolymarketDataSource()
            self.news = NewsDataSource()
            self.social = SocialDataSource()

        # Track last scan
        self.last_scan_time: Optional[datetime] = None
        self.last_scan_result: Optional[ScanResult] = None

    async def get_markets_to_scan(
        self,
        override_slugs: Optional[list[str]] = None,
    ) -> list[Market]:
        """
        Get list of markets to scan.

        Args:
            override_slugs: If provided, use these slugs instead of config watchlist

        Returns:
            List of Market objects to scan
        """
        markets = []
        slugs_to_fetch = override_slugs or self.settings.watchlist

        # Fetch watchlist markets by slug
        if slugs_to_fetch:
            logger.info(f"Fetching {len(slugs_to_fetch)} markets from watchlist")
            skipped_markets = []
            for slug in slugs_to_fetch:
                try:
                    # require_current=True filters closed/expired markets
                    market = await self.polymarket.get_market_by_slug(slug, require_current=True)
                    if market:
                        markets.append(market)
                        logger.debug(f"Found active market: {slug}")
                    else:
                        # Try fetching without current filter to see if it exists but is closed
                        closed_market = await self.polymarket.get_market_by_slug(slug, require_current=False)
                        if closed_market:
                            skipped_markets.append(f"{slug} (closed/expired)")
                            logger.info(f"Skipping closed/expired market: {slug}")
                        else:
                            logger.warning(f"Market not found: {slug}")
                except Exception as e:
                    logger.error(f"Error fetching market {slug}: {e}")

            if skipped_markets:
                logger.warning(
                    f"Skipped {len(skipped_markets)} closed/expired markets from watchlist: "
                    f"{', '.join(skipped_markets)}"
                )

        # Optionally discover additional markets
        if self.settings.signal_discovery_enabled and not override_slugs:
            discovered = await self._discover_markets(
                exclude_ids={m.id for m in markets},
                max_markets=self.settings.signal_discovery_max_markets,
                min_volume=self.settings.signal_discovery_min_volume,
            )
            markets.extend(discovered)
            logger.info(f"Discovered {len(discovered)} additional markets")

        return markets

    async def _discover_markets(
        self,
        exclude_ids: set[str],
        max_markets: int,
        min_volume: float,
    ) -> list[Market]:
        """
        Discover high-volume markets not in watchlist.

        Applies quality filters:
        - Must be active and not closed
        - Must have price between MIN_PRICE_FOR_SIGNALS and MAX_PRICE_FOR_SIGNALS
        - Must have at least MIN_DAYS_TO_EXPIRY before expiration
        - Must meet minimum volume threshold
        """
        try:
            # Fetch active markets - filter_current=True removes closed/expired
            all_markets = await self.polymarket.get_markets(
                active=True,
                limit=100,  # Fetch more to have enough after filtering
                filter_current=True,
            )

            # Apply quality filters
            settings = self.settings
            discovered = []
            for m in all_markets:
                # Skip already-included markets
                if m.id in exclude_ids:
                    continue

                # Skip below minimum volume
                if m.volume < min_volume:
                    continue

                # Skip extreme prices (use same thresholds as signal generator)
                if m.current_price is not None:
                    if m.current_price < settings.min_price_for_signals:
                        continue
                    if m.current_price > settings.max_price_for_signals:
                        continue

                discovered.append(m)
                logger.debug(
                    f"Discovered market: {m.slug} (price={m.current_price:.1%}, "
                    f"volume=${m.volume:,.0f})"
                )

            # Sort by volume and take top N
            discovered.sort(key=lambda m: m.volume, reverse=True)
            result = discovered[:max_markets]

            if result:
                logger.info(
                    f"Discovered {len(result)} markets: "
                    f"{', '.join(m.slug[:30] for m in result)}"
                )

            return result

        except Exception as e:
            logger.error(f"Error discovering markets: {e}")
            return []

    async def _get_news_sentiment(self, market: Market) -> Optional[NewsSentiment]:
        """Get news sentiment for a market, handling config and errors."""
        if self.settings.skip_news_api:
            return None

        try:
            # Extract search query from market question
            query = self._extract_search_query(market.question)
            if hasattr(self.news, 'get_sentiment_for_market'):
                return await self.news.get_sentiment_for_market(market.id, query)
            else:
                # Real API - need to search and aggregate
                articles = await self.news.search_news(query=query, page_size=10)
                if not articles:
                    return None
                # Simple sentiment aggregation (would use NLP in production)
                return NewsSentiment(
                    market_id=market.id,
                    sentiment_score=0.0,  # Neutral without NLP
                    confidence=min(1.0, len(articles) / 10),
                    article_count=len(articles),
                    top_headlines=[a.title for a in articles[:5]],
                    sources=list(set(a.source.name for a in articles if a.source)),
                )
        except Exception as e:
            logger.warning(f"Failed to get news sentiment for {market.id}: {e}")
            return None

    async def _get_social_data(
        self,
        market: Market,
    ) -> tuple[Optional[SocialMention], Optional[SocialSentiment]]:
        """Get social data for a market, handling config and errors."""
        if self.settings.skip_social_api:
            return None, None

        try:
            query = self._extract_search_query(market.question)

            if hasattr(self.social, 'get_mentions_for_market'):
                mentions = await self.social.get_mentions_for_market(market.id, query)
            else:
                mentions = None

            if hasattr(self.social, 'get_sentiment_for_market'):
                sentiment = await self.social.get_sentiment_for_market(market.id, query)
            else:
                sentiment = None

            return mentions, sentiment

        except Exception as e:
            logger.warning(f"Failed to get social data for {market.id}: {e}")
            return None, None

    def _extract_search_query(self, question: str) -> str:
        """Extract a search query from a market question."""
        # Remove common prefixes
        query = question.replace("Will ", "").replace("?", "")

        # Take first few significant words
        words = query.split()[:5]
        return " ".join(words)

    async def scan_market(self, market: Market) -> list[Signal]:
        """
        Scan a single market for signals.

        Handles API failures gracefully by continuing with available data.
        """
        # Get external data (may be None if APIs unavailable)
        news_sentiment = await self._get_news_sentiment(market)
        social_mentions, social_sentiment = await self._get_social_data(market)

        # Generate signals with whatever data we have
        signals = await self.generator.process_market(
            market=market,
            news_sentiment=news_sentiment,
            social_mentions=social_mentions,
            social_sentiment=social_sentiment,
            persist=False,  # Don't persist during scan, let caller decide
        )

        return signals

    async def run_scan(
        self,
        override_markets: Optional[list[str]] = None,
        persist: bool = True,
    ) -> ScanResult:
        """
        Run a full signal scan.

        Args:
            override_markets: Optional list of market slugs to scan instead of watchlist
            persist: Whether to persist generated signals to database

        Returns:
            ScanResult with all generated signals and status info
        """
        result = ScanResult()
        logger.info("Starting signal scan...")

        # Get markets to scan
        markets = await self.get_markets_to_scan(override_slugs=override_markets)
        if not markets:
            result.errors.append("No markets to scan. Check watchlist configuration.")
            logger.warning("No markets found to scan")
            return result

        logger.info(f"Scanning {len(markets)} markets")

        # Scan each market
        for market in markets:
            try:
                signals = await self.scan_market(market)
                result.signals.extend(signals)
                result.markets_scanned += 1

                if signals:
                    logger.info(
                        f"Market {market.slug}: Generated {len(signals)} signal(s)"
                    )

            except Exception as e:
                error_msg = f"Error scanning market {market.slug}: {str(e)}"
                result.errors.append(error_msg)
                logger.error(error_msg)

        result.signals_generated = len(result.signals)

        # Persist signals if requested
        if persist and result.signals:
            await self._persist_signals(result.signals, markets)

        # Record degradation status
        result.degraded = {
            "news_api": self.settings.skip_news_api or not get_rate_limiter("newsapi").is_available(),
            "social_api": self.settings.skip_social_api or not get_rate_limiter("twitter").is_available(),
            "polymarket_api": not get_rate_limiter("polymarket").is_available(),
        }

        # Update last scan tracking
        self.last_scan_time = result.scan_time
        self.last_scan_result = result

        logger.info(
            f"Scan complete: {result.signals_generated} signals from "
            f"{result.markets_scanned} markets"
        )

        return result

    async def _persist_signals(self, signals: list[Signal], markets: list[Market]) -> None:
        """Persist signals to database, upserting markets first."""
        try:
            db = get_supabase_client()

            # First upsert all markets to satisfy foreign key constraint
            if markets:
                await db.upsert_markets(markets)
                logger.info(f"Upserted {len(markets)} markets")

            # Then persist signals
            for signal in signals:
                await db.create_signal(signal)
                logger.info(f"Persisted signal {signal.id}")
        except Exception as e:
            logger.error(f"Failed to persist signals: {e}")

    def get_status(self) -> dict:
        """Get current scanner status."""
        api_status = get_all_api_status()

        # Add configured disabled status
        if self.settings.skip_news_api:
            api_status["newsapi"] = {"available": False, "reason": "disabled_by_config"}
        if self.settings.skip_social_api:
            api_status["twitter"] = {"available": False, "reason": "disabled_by_config"}

        return {
            "watchlist": self.settings.watchlist,
            "discovery_enabled": self.settings.signal_discovery_enabled,
            "min_confidence": self.settings.signal_min_confidence,
            "apis": api_status,
            "last_scan": self.last_scan_time.isoformat() if self.last_scan_time else None,
            "last_scan_signals": self.last_scan_result.signals_generated if self.last_scan_result else 0,
        }


# Global scanner instance
_scanner: Optional[SignalScanner] = None


def get_scanner() -> SignalScanner:
    """Get or create the global scanner instance."""
    global _scanner
    if _scanner is None:
        _scanner = SignalScanner()
    return _scanner
