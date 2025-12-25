"""Signal generation rules - the core logic for detecting opportunities."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from src.config import get_settings
from src.models.market import Market
from src.models.news import NewsSentiment
from src.models.social import SocialMention, SocialSentiment
from src.models.signal import SignalType, SignalDirection


@dataclass
class SignalCandidate:
    """A potential signal detected by a rule."""

    signal_type: SignalType
    direction: SignalDirection
    confidence: float  # 0.0 to 1.0
    reasoning: str

    # Context that triggered the signal
    news_sentiment_score: Optional[float] = None
    social_mention_count_24h: Optional[int] = None
    social_sentiment_score: Optional[float] = None


class SignalRule(ABC):
    """Abstract base class for signal generation rules."""

    @abstractmethod
    def evaluate(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        previous_price: Optional[float] = None,
        previous_volume_24h: Optional[float] = None,
    ) -> Optional[SignalCandidate]:
        """
        Evaluate the rule against current market state.

        Returns SignalCandidate if conditions are met, None otherwise.
        """
        pass


class SentimentDivergenceRule(SignalRule):
    """
    Detects when news sentiment diverges from market price.

    Theory: If news is overwhelmingly positive but price is low (or vice versa),
    the market may be mispriced and will correct.

    IMPORTANT: Only triggers on STRONG directional sentiment, not neutral.
    Neutral sentiment (near 0) should NOT generate signals.

    Trigger: Strong sentiment (|score| > 0.3) with price that contradicts it
    Direction: BUY if bullish sentiment + low price, SELL if bearish sentiment + high price
    """

    def __init__(self, threshold: Optional[float] = None):
        settings = get_settings()
        self.threshold = threshold or settings.sentiment_divergence_threshold
        self.min_sentiment_strength = settings.min_sentiment_strength
        self.min_article_count = settings.min_article_count

    def evaluate(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        previous_price: Optional[float] = None,
        previous_volume_24h: Optional[float] = None,
    ) -> Optional[SignalCandidate]:
        if not news_sentiment or market.current_price is None:
            return None

        sentiment = news_sentiment.sentiment_score
        price = market.current_price

        # CRITICAL: Require strong directional sentiment, not neutral
        # Neutral sentiment should NEVER generate signals
        if abs(sentiment) < self.min_sentiment_strength:
            return None

        # Require minimum article count for statistical confidence
        if news_sentiment.article_count < self.min_article_count:
            return None

        # Skip extreme price markets - sentiment signals unreliable at edges
        if price < 0.05 or price > 0.95:
            return None

        # Determine direction based on sentiment vs price relationship
        # Bullish sentiment (> 0.3) with low price = potential BUY
        # Bearish sentiment (< -0.3) with high price = potential SELL

        if sentiment > self.min_sentiment_strength:
            # Bullish sentiment - only signal if price has room to grow
            if price > 0.70:
                # Price already high, no clear edge
                return None

            # Calculate how much the price "should" be higher given bullish news
            # Bullish news on a low-priced market = opportunity
            price_expectation = 0.5 + (sentiment * 0.3)  # Maps 0.3-1.0 sentiment to 0.59-0.80
            divergence = price_expectation - price

            if divergence < self.threshold:
                return None

            direction = SignalDirection.BUY
            reasoning = (
                f"Strongly positive news sentiment ({sentiment:+.2f}) suggests higher probability "
                f"than current price ({price:.0%}). Based on {news_sentiment.article_count} articles, "
                f"the market appears undervalued by {divergence:.0%}."
            )

        else:  # sentiment < -self.min_sentiment_strength
            # Bearish sentiment - only signal if price has room to fall
            if price < 0.30:
                # Price already low, no clear edge
                return None

            # Calculate how much the price "should" be lower given bearish news
            price_expectation = 0.5 + (sentiment * 0.3)  # Maps -0.3 to -1.0 sentiment to 0.41-0.20
            divergence = price - price_expectation

            if divergence < self.threshold:
                return None

            direction = SignalDirection.SELL
            reasoning = (
                f"Strongly negative news sentiment ({sentiment:+.2f}) suggests lower probability "
                f"than current price ({price:.0%}). Based on {news_sentiment.article_count} articles, "
                f"the market appears overvalued by {divergence:.0%}."
            )

        # Confidence based on:
        # 1. Sentiment strength (stronger = more confident)
        # 2. Divergence magnitude (larger = more confident)
        # 3. Article count (more articles = more confident)
        sentiment_factor = min(1.0, abs(sentiment) / 0.6)  # 0.6+ sentiment = full credit
        divergence_factor = min(1.0, divergence / 0.30)  # 30%+ divergence = full credit
        article_factor = min(1.0, news_sentiment.article_count / 15)  # 15+ articles = full credit

        confidence = (sentiment_factor * 0.4 + divergence_factor * 0.4 + article_factor * 0.2)
        confidence = max(0.3, min(0.9, confidence))  # Cap between 0.3 and 0.9

        return SignalCandidate(
            signal_type=SignalType.SENTIMENT_DIVERGENCE,
            direction=direction,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            news_sentiment_score=sentiment,
        )


class VolumeSurgeRule(SignalRule):
    """
    Detects when trading volume surges with price movement.

    Theory: Significant volume increase with price movement indicates
    informed trading - follow the momentum.

    Trigger: volume_24h > multiplier * average_volume AND price_change > threshold
    Direction: Follow the price momentum
    """

    def __init__(
        self,
        volume_multiplier: Optional[float] = None,
        price_change_threshold: float = 0.05,
    ):
        settings = get_settings()
        self.volume_multiplier = volume_multiplier or settings.volume_surge_multiplier
        self.price_change_threshold = price_change_threshold

    def evaluate(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        previous_price: Optional[float] = None,
        previous_volume_24h: Optional[float] = None,
    ) -> Optional[SignalCandidate]:
        if previous_price is None or previous_volume_24h is None:
            return None
        if market.current_price is None or previous_volume_24h == 0:
            return None

        # Calculate volume surge
        volume_ratio = market.volume_24h / previous_volume_24h

        if volume_ratio < self.volume_multiplier:
            return None

        # Calculate price change
        price_change = (market.current_price - previous_price) / previous_price

        if abs(price_change) < self.price_change_threshold:
            return None

        # Follow the momentum
        if price_change > 0:
            direction = SignalDirection.BUY
            reasoning = (
                f"Volume surged {volume_ratio:.1f}x (from ${previous_volume_24h:,.0f} to "
                f"${market.volume_24h:,.0f}) with price rising {price_change*100:+.1f}%. "
                f"Strong buying pressure suggests continued upward momentum."
            )
        else:
            direction = SignalDirection.SELL
            reasoning = (
                f"Volume surged {volume_ratio:.1f}x (from ${previous_volume_24h:,.0f} to "
                f"${market.volume_24h:,.0f}) with price falling {price_change*100:+.1f}%. "
                f"Strong selling pressure suggests continued downward momentum."
            )

        # Confidence based on volume multiple (3x = 0.5, 5x+ = 1.0)
        confidence = min(1.0, (volume_ratio - self.volume_multiplier) / 2 + 0.5)

        return SignalCandidate(
            signal_type=SignalType.VOLUME_SURGE,
            direction=direction,
            confidence=round(confidence, 2),
            reasoning=reasoning,
        )


class SocialSpikeRule(SignalRule):
    """
    Detects when social media activity spikes with clear sentiment.

    Theory: Viral social activity often precedes price movements.
    If sentiment is strongly directional, follow it.

    Trigger: mentions > multiplier * average AND |sentiment| > threshold
    Direction: Follow the sentiment direction
    """

    def __init__(
        self,
        mention_multiplier: Optional[float] = None,
        sentiment_threshold: float = 0.3,
    ):
        settings = get_settings()
        self.mention_multiplier = mention_multiplier or settings.social_spike_multiplier
        self.sentiment_threshold = sentiment_threshold

    def evaluate(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        previous_price: Optional[float] = None,
        previous_volume_24h: Optional[float] = None,
    ) -> Optional[SignalCandidate]:
        if not social_mentions or not social_sentiment:
            return None

        # Check for mention spike
        # Compare 1h to average hourly rate (24h / 24)
        avg_hourly = social_mentions.mention_count_24h / 24 if social_mentions.mention_count_24h else 1
        hourly_ratio = social_mentions.mention_count_1h / avg_hourly if avg_hourly > 0 else 0

        if hourly_ratio < self.mention_multiplier:
            return None

        # Check sentiment is strongly directional
        if abs(social_sentiment.sentiment_score) < self.sentiment_threshold:
            return None

        # Follow sentiment direction
        if social_sentiment.sentiment_score > 0:
            direction = SignalDirection.BUY
            reasoning = (
                f"Social mentions spiked {hourly_ratio:.1f}x above average "
                f"({social_mentions.mention_count_1h} in last hour vs {avg_hourly:.0f}/hr average) "
                f"with strongly positive sentiment ({social_sentiment.sentiment_score:+.2f}). "
                f"Viral bullish activity may drive price higher."
            )
        else:
            direction = SignalDirection.SELL
            reasoning = (
                f"Social mentions spiked {hourly_ratio:.1f}x above average "
                f"({social_mentions.mention_count_1h} in last hour vs {avg_hourly:.0f}/hr average) "
                f"with strongly negative sentiment ({social_sentiment.sentiment_score:+.2f}). "
                f"Viral bearish activity may drive price lower."
            )

        # Confidence based on spike magnitude and sentiment strength
        spike_confidence = min(1.0, (hourly_ratio - self.mention_multiplier) / self.mention_multiplier + 0.5)
        sentiment_confidence = abs(social_sentiment.sentiment_score)
        confidence = (spike_confidence + sentiment_confidence) / 2

        return SignalCandidate(
            signal_type=SignalType.SOCIAL_SPIKE,
            direction=direction,
            confidence=round(confidence, 2),
            reasoning=reasoning,
            social_mention_count_24h=social_mentions.mention_count_24h,
            social_sentiment_score=social_sentiment.sentiment_score,
        )


class PriceMomentumRule(SignalRule):
    """
    Detects significant price momentum.

    Theory: Large price movements often continue in the short term.
    Volume confirmation increases reliability.

    Trigger: price_change > threshold with volume confirmation
    Direction: Follow the momentum
    """

    def __init__(
        self,
        price_threshold: Optional[float] = None,
        min_volume_ratio: float = 1.5,
    ):
        settings = get_settings()
        self.price_threshold = price_threshold or settings.price_momentum_threshold
        self.min_volume_ratio = min_volume_ratio

    def evaluate(
        self,
        market: Market,
        news_sentiment: Optional[NewsSentiment] = None,
        social_mentions: Optional[SocialMention] = None,
        social_sentiment: Optional[SocialSentiment] = None,
        previous_price: Optional[float] = None,
        previous_volume_24h: Optional[float] = None,
    ) -> Optional[SignalCandidate]:
        if previous_price is None or market.current_price is None:
            return None

        # Calculate price change
        price_change = (market.current_price - previous_price) / previous_price

        if abs(price_change) < self.price_threshold:
            return None

        # Check volume confirmation
        volume_confirmed = False
        if previous_volume_24h and previous_volume_24h > 0:
            volume_ratio = market.volume_24h / previous_volume_24h
            volume_confirmed = volume_ratio >= self.min_volume_ratio

        # Need either volume confirmation or very large price move
        if not volume_confirmed and abs(price_change) < self.price_threshold * 1.5:
            return None

        # Follow momentum
        if price_change > 0:
            direction = SignalDirection.BUY
            vol_note = f" with {volume_ratio:.1f}x volume increase" if volume_confirmed else ""
            reasoning = (
                f"Price jumped {price_change*100:+.1f}%{vol_note}. "
                f"Strong upward momentum suggests continued gains in the short term."
            )
        else:
            direction = SignalDirection.SELL
            vol_note = f" with {volume_ratio:.1f}x volume increase" if volume_confirmed else ""
            reasoning = (
                f"Price dropped {price_change*100:+.1f}%{vol_note}. "
                f"Strong downward momentum suggests continued decline in the short term."
            )

        # Confidence based on price move magnitude and volume confirmation
        base_confidence = min(1.0, abs(price_change) / self.price_threshold * 0.5)
        if volume_confirmed:
            base_confidence += 0.3
        confidence = min(1.0, base_confidence)

        return SignalCandidate(
            signal_type=SignalType.PRICE_MOMENTUM,
            direction=direction,
            confidence=round(confidence, 2),
            reasoning=reasoning,
        )
