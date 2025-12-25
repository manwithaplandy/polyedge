"""Signal generator - orchestrates rule evaluation and signal creation."""

import logging
from datetime import datetime, timezone
from typing import Optional

from src.config import get_settings, Settings
from src.db.client import SupabaseClient
from src.models.market import Market, MarketTier
from src.models.signal import Signal, SignalCreate, SignalType
from src.models.news import NewsSentiment
from src.models.social import SocialMention, SocialSentiment
from src.services.signals.rules import (
    SignalRule,
    SignalCandidate,
    SentimentDivergenceRule,
    VolumeSurgeRule,
    SocialSpikeRule,
    PriceMomentumRule,
)

logger = logging.getLogger(__name__)


class SignalGenerator:
    """
    Generates trade signals by evaluating rules against market state.

    This is the core engine that powers PolyEdge's value proposition.
    """

    def __init__(
        self,
        db_client: Optional[SupabaseClient] = None,
        min_confidence: float = 0.5,
    ):
        self.db_client = db_client
        self.min_confidence = min_confidence

        # Initialize rules
        self.rules: list[SignalRule] = [
            SentimentDivergenceRule(),
            VolumeSurgeRule(),
            SocialSpikeRule(),
            PriceMomentumRule(),
        ]

        # Cache for previous market states (for momentum/surge detection)
        self._previous_states: dict[str, dict] = {}

        # Load settings for quality filtering
        self._settings = get_settings()

    def should_skip_market(self, market: Market) -> tuple[bool, str]:
        """
        Check if market should be skipped for signal generation.

        Returns (should_skip, reason) tuple.
        """
        settings = self._settings

        # Skip closed or archived markets
        if market.closed:
            return True, "Market is closed"
        if market.archived:
            return True, "Market is archived"
        if not market.accepting_orders:
            return True, "Market is not accepting orders"

        # Skip markets too close to expiration or already expired
        if market.end_date:
            # Handle timezone-aware dates
            end_date = market.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_to_expiry = (end_date - now).days

            # Skip if already expired
            if end_date < now:
                return True, "Market has already expired"

            if days_to_expiry < settings.min_days_to_expiry:
                return True, f"Market expires in {days_to_expiry} days (min: {settings.min_days_to_expiry})"

        # Skip THIN tier markets (too illiquid)
        tier = market.tier or market.compute_tier()
        tier_order = {"THIN": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3}
        min_tier_value = tier_order.get(settings.min_market_tier.upper(), 1)

        if tier_order.get(tier.value, 0) < min_tier_value:
            return True, f"Market tier {tier.value} below minimum {settings.min_market_tier}"

        # Skip extreme price markets
        if market.current_price is not None:
            if market.current_price < settings.min_price_for_signals:
                return True, f"Price {market.current_price:.2%} below minimum {settings.min_price_for_signals:.0%}"
            if market.current_price > settings.max_price_for_signals:
                return True, f"Price {market.current_price:.2%} above maximum {settings.max_price_for_signals:.0%}"

        return False, ""

    def adjust_confidence_for_quality(
        self, candidate: SignalCandidate, market: Market
    ) -> float:
        """Adjust signal confidence based on market quality factors."""
        confidence = candidate.confidence
        tier = market.tier or market.compute_tier()

        # Tier adjustments
        if tier == MarketTier.LOW:
            confidence *= 0.85  # 15% penalty for low volume
        elif tier == MarketTier.MEDIUM:
            confidence *= 0.95  # 5% penalty
        # HIGH tier = no penalty

        # Expiration adjustments
        if market.end_date:
            end_date = market.end_date
            if end_date.tzinfo is None:
                end_date = end_date.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            days_to_expiry = (end_date - now).days

            if days_to_expiry < 14:
                # Linear decay for markets approaching expiration
                confidence *= max(0.5, days_to_expiry / 14)

        return max(0.0, min(1.0, confidence))

    def add_rule(self, rule: SignalRule) -> None:
        """Add a custom signal rule."""
        self.rules.append(rule)

    def set_previous_state(
        self,
        market_id: str,
        price: float,
        volume_24h: float,
    ) -> None:
        """Store previous market state for comparison."""
        self._previous_states[market_id] = {
            "price": price,
            "volume_24h": volume_24h,
            "timestamp": datetime.utcnow(),
        }

    def get_previous_state(self, market_id: str) -> Optional[dict]:
        """Get stored previous state for a market."""
        return self._previous_states.get(market_id)

    async def evaluate_market(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
    ) -> list[SignalCandidate]:
        """
        Evaluate all rules against a market's current state.

        Returns list of signal candidates that passed rule thresholds.
        """
        candidates = []

        # Get previous state for comparison
        prev_state = self.get_previous_state(market.id)
        previous_price = prev_state["price"] if prev_state else None
        previous_volume_24h = prev_state["volume_24h"] if prev_state else None

        for rule in self.rules:
            try:
                candidate = rule.evaluate(
                    market=market,
                    news_sentiment=news_sentiment,
                    social_mentions=social_mentions,
                    social_sentiment=social_sentiment,
                    previous_price=previous_price,
                    previous_volume_24h=previous_volume_24h,
                )

                if candidate and candidate.confidence >= self.min_confidence:
                    candidates.append(candidate)

            except Exception as e:
                logger.error(
                    f"Error evaluating rule {rule.__class__.__name__} for market {market.id}: {e}"
                )

        # Update stored state for next evaluation
        if market.current_price is not None:
            self.set_previous_state(market.id, market.current_price, market.volume_24h)

        return candidates

    async def generate_signal(
        self,
        market: Market,
        candidate: SignalCandidate,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
    ) -> Signal:
        """
        Create a Signal from a SignalCandidate with full market context.
        """
        signal = Signal(
            # Market context
            market_id=market.id,
            market_question=market.question,
            market_slug=market.slug,
            market_end_date=market.end_date,
            # Signal details
            signal_type=candidate.signal_type,
            direction=candidate.direction,
            confidence=candidate.confidence,
            reasoning=candidate.reasoning,
            # Market state at signal time
            entry_price=market.current_price or 0.5,
            entry_volume_24h=market.volume_24h,
            entry_volume_total=market.volume,
            entry_liquidity=market.liquidity,
            market_tier=market.tier or market.compute_tier(),
            # External context
            news_sentiment_score=candidate.news_sentiment_score,
            social_mention_count_24h=candidate.social_mention_count_24h,
            social_sentiment_score=candidate.social_sentiment_score,
        )

        # Fill in any missing context from sources
        if news_sentiment and signal.news_sentiment_score is None:
            signal.news_sentiment_score = news_sentiment.sentiment_score

        if social_mentions and signal.social_mention_count_24h is None:
            signal.social_mention_count_24h = social_mentions.mention_count_24h

        return signal

    async def process_market(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        persist: bool = True,
    ) -> list[Signal]:
        """
        Full pipeline: evaluate market, generate signals, optionally persist.

        Returns list of generated signals.
        """
        signals = []

        # Check if market should be skipped for quality reasons
        should_skip, skip_reason = self.should_skip_market(market)
        if should_skip:
            logger.debug(f"Skipping market {market.slug}: {skip_reason}")
            return signals

        # Evaluate all rules
        candidates = await self.evaluate_market(
            market=market,
            news_sentiment=news_sentiment,
            social_mentions=social_mentions,
            social_sentiment=social_sentiment,
        )

        if not candidates:
            return signals

        # Filter and adjust candidates based on quality
        qualified_candidates = []
        for candidate in candidates:
            # Adjust confidence for market quality
            adjusted_confidence = self.adjust_confidence_for_quality(candidate, market)

            # Only keep if still above minimum confidence after adjustment
            if adjusted_confidence >= self.min_confidence:
                candidate.confidence = adjusted_confidence
                qualified_candidates.append(candidate)
            else:
                logger.debug(
                    f"Dropping {candidate.signal_type.value} signal for {market.slug}: "
                    f"confidence {adjusted_confidence:.2f} below threshold after quality adjustment"
                )

        # Generate signals from qualified candidates
        for candidate in qualified_candidates:
            signal = await self.generate_signal(
                market=market,
                candidate=candidate,
                news_sentiment=news_sentiment,
                social_mentions=social_mentions,
            )
            signals.append(signal)

            logger.info(
                f"Generated {signal.signal_type.value} signal for {market.question[:50]}... "
                f"Direction: {signal.direction.value}, Confidence: {signal.confidence}"
            )

            # Persist to database if client available and persistence enabled
            if persist and self.db_client:
                try:
                    await self.db_client.create_signal(signal)
                    logger.info(f"Persisted signal {signal.id}")
                except Exception as e:
                    logger.error(f"Failed to persist signal: {e}")

        return signals

    async def run_scan(
        self,
        markets: list[Market],
        get_news_sentiment: callable = None,
        get_social_mentions: callable = None,
        get_social_sentiment: callable = None,
        persist: bool = True,
    ) -> list[Signal]:
        """
        Scan multiple markets for signals.

        Args:
            markets: List of markets to scan
            get_news_sentiment: Async function to get news sentiment for a market
            get_social_mentions: Async function to get social mentions for a market
            get_social_sentiment: Async function to get social sentiment for a market
            persist: Whether to persist signals to database

        Returns:
            All generated signals from the scan
        """
        all_signals = []

        for market in markets:
            # Gather context for this market
            news_sentiment = None
            social_mentions = None
            social_sentiment = None

            if get_news_sentiment:
                try:
                    news_sentiment = await get_news_sentiment(market)
                except Exception as e:
                    logger.warning(f"Failed to get news sentiment for {market.id}: {e}")

            if get_social_mentions:
                try:
                    social_mentions = await get_social_mentions(market)
                except Exception as e:
                    logger.warning(f"Failed to get social mentions for {market.id}: {e}")

            if get_social_sentiment:
                try:
                    social_sentiment = await get_social_sentiment(market)
                except Exception as e:
                    logger.warning(f"Failed to get social sentiment for {market.id}: {e}")

            # Process this market
            signals = await self.process_market(
                market=market,
                news_sentiment=news_sentiment,
                social_mentions=social_mentions,
                social_sentiment=social_sentiment,
                persist=persist,
            )

            all_signals.extend(signals)

        logger.info(f"Scan complete: {len(all_signals)} signals generated from {len(markets)} markets")
        return all_signals


class MockSignalGenerator(SignalGenerator):
    """Signal generator with mock data for testing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # Pre-seed some previous states to enable momentum/surge detection
        self._seed_previous_states()

    def _seed_previous_states(self) -> None:
        """Seed previous states for mock markets."""
        # These will allow volume surge and momentum signals to trigger
        mock_states = {
            "mock-trump-2024": {"price": 0.48, "volume_24h": 150_000},
            "mock-harris-2024": {"price": 0.50, "volume_24h": 120_000},
            "mock-btc-100k": {"price": 0.65, "volume_24h": 40_000},
            "mock-fed-rate-jan": {"price": 0.40, "volume_24h": 15_000},
        }

        for market_id, state in mock_states.items():
            self.set_previous_state(market_id, state["price"], state["volume_24h"])
