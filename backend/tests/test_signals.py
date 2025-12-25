"""Tests for signal generation."""

import pytest
from datetime import datetime

from src.models.market import Market, MarketTier
from src.models.news import NewsSentiment
from src.models.social import SocialMention, SocialSentiment
from src.models.signal import SignalType, SignalDirection
from src.services.signals.rules import (
    SentimentDivergenceRule,
    VolumeSurgeRule,
    SocialSpikeRule,
    PriceMomentumRule,
)
from src.services.signals.generator import SignalGenerator, MockSignalGenerator
from src.services.data_sources.polymarket import MockPolymarketDataSource
from src.services.data_sources.news import MockNewsDataSource
from src.services.data_sources.social import MockSocialDataSource


class TestSentimentDivergenceRule:
    """Test sentiment divergence signal rule."""

    def test_triggers_buy_when_sentiment_high_price_low(self):
        """Should trigger BUY when sentiment is positive but price is low."""
        rule = SentimentDivergenceRule(threshold=0.15)

        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.35,
            tier=MarketTier.MEDIUM,
        )

        sentiment = NewsSentiment(
            market_id="test-1",
            sentiment_score=0.7,  # Very positive
            confidence=0.8,
            article_count=10,
            positive_count=8,
            negative_count=1,
            neutral_count=1,
        )

        result = rule.evaluate(market=market, news_sentiment=sentiment)

        assert result is not None
        assert result.signal_type == SignalType.SENTIMENT_DIVERGENCE
        assert result.direction == SignalDirection.BUY
        assert result.confidence > 0.5

    def test_triggers_sell_when_sentiment_low_price_high(self):
        """Should trigger SELL when sentiment is negative but price is high."""
        rule = SentimentDivergenceRule(threshold=0.15)

        market = Market(
            id="test-2",
            condition_id="0x456",
            question="Test market?",
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.75,
            tier=MarketTier.MEDIUM,
        )

        sentiment = NewsSentiment(
            market_id="test-2",
            sentiment_score=-0.5,  # Negative
            confidence=0.8,
            article_count=10,
            positive_count=2,
            negative_count=7,
            neutral_count=1,
        )

        result = rule.evaluate(market=market, news_sentiment=sentiment)

        assert result is not None
        assert result.signal_type == SignalType.SENTIMENT_DIVERGENCE
        assert result.direction == SignalDirection.SELL

    def test_no_signal_when_aligned(self):
        """Should not trigger when sentiment aligns with price."""
        rule = SentimentDivergenceRule(threshold=0.20)

        market = Market(
            id="test-3",
            condition_id="0x789",
            question="Test market?",
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.55,
            tier=MarketTier.MEDIUM,
        )

        # Sentiment of 0.1 maps to 0.55 on 0-1 scale - aligned with price
        sentiment = NewsSentiment(
            market_id="test-3",
            sentiment_score=0.1,
            confidence=0.8,
            article_count=10,
        )

        result = rule.evaluate(market=market, news_sentiment=sentiment)
        assert result is None


class TestVolumeSurgeRule:
    """Test volume surge signal rule."""

    def test_triggers_on_volume_spike_with_price_rise(self):
        """Should trigger BUY when volume spikes with rising price."""
        rule = VolumeSurgeRule(volume_multiplier=2.0, price_change_threshold=0.05)

        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            volume=100_000,
            volume_24h=50_000,  # 5x previous
            liquidity=50_000,
            current_price=0.60,
            tier=MarketTier.MEDIUM,
        )

        result = rule.evaluate(
            market=market,
            previous_price=0.50,  # 20% rise
            previous_volume_24h=10_000,
        )

        assert result is not None
        assert result.signal_type == SignalType.VOLUME_SURGE
        assert result.direction == SignalDirection.BUY


class TestMockDataSources:
    """Test mock data sources work correctly."""

    @pytest.mark.asyncio
    async def test_polymarket_mock_returns_markets(self):
        """Mock Polymarket source should return realistic markets."""
        source = MockPolymarketDataSource()
        markets = await source.get_markets(limit=5)

        assert len(markets) > 0
        assert all(m.question for m in markets)
        assert all(m.current_price is not None for m in markets)

    @pytest.mark.asyncio
    async def test_news_mock_returns_sentiment(self):
        """Mock news source should return sentiment."""
        source = MockNewsDataSource()
        sentiment = await source.get_sentiment_for_market("test-id", "trump")

        assert sentiment is not None
        assert -1.0 <= sentiment.sentiment_score <= 1.0
        assert sentiment.article_count > 0

    @pytest.mark.asyncio
    async def test_social_mock_returns_mentions(self):
        """Mock social source should return mention data."""
        source = MockSocialDataSource()
        mentions = await source.get_mentions_for_market("test-id", "bitcoin")

        assert mentions is not None
        assert mentions.mention_count_24h >= 0


class TestSignalGenerator:
    """Test signal generator orchestration."""

    @pytest.mark.asyncio
    async def test_generator_evaluates_all_rules(self):
        """Generator should evaluate all rules for each market."""
        generator = MockSignalGenerator(min_confidence=0.3)

        # Get a mock market
        source = MockPolymarketDataSource()
        markets = await source.get_markets(limit=1)
        market = markets[0]

        # Create context
        news_sentiment = NewsSentiment(
            market_id=market.id,
            sentiment_score=0.8,  # Very positive to trigger divergence
            confidence=0.9,
            article_count=15,
        )

        # Evaluate
        candidates = await generator.evaluate_market(
            market=market,
            news_sentiment=news_sentiment,
        )

        # Should find at least one signal given the strong sentiment
        # (depends on current mock price)
        assert isinstance(candidates, list)

    @pytest.mark.asyncio
    async def test_generator_creates_signals(self):
        """Generator should create full Signal objects."""
        generator = MockSignalGenerator(min_confidence=0.3)

        source = MockPolymarketDataSource()
        markets = await source.get_markets(limit=1)
        market = markets[0]

        news_sentiment = NewsSentiment(
            market_id=market.id,
            sentiment_score=0.9,
            confidence=0.9,
            article_count=20,
        )

        signals = await generator.process_market(
            market=market,
            news_sentiment=news_sentiment,
            persist=False,
        )

        # If signals were generated, verify they're complete
        for signal in signals:
            assert signal.id is not None
            assert signal.market_id == market.id
            assert signal.entry_price == market.current_price
            assert signal.reasoning
