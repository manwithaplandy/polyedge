"""Social media data source with real (Twitter/X) and mock implementations."""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

import httpx

from src.config import get_settings
from src.models.social import (
    Tweet,
    TwitterSearchResponse,
    TwitterCountResponse,
    TweetCountBucket,
    TwitterPublicMetrics,
    SocialMention,
    SocialSentiment,
)
from src.services.data_sources.base import DataSourceBase
from src.services.data_sources.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class SocialDataSource(DataSourceBase):
    """Real Twitter/X API v2 data source."""

    BASE_URL = "https://api.x.com/2"

    def __init__(self, bearer_token: Optional[str] = None):
        settings = get_settings()
        self.bearer_token = bearer_token or settings.twitter_bearer_token
        self.timeout = 30.0
        self.rate_limiter = get_rate_limiter("twitter")

    async def health_check(self) -> bool:
        """Check if Twitter API is available."""
        if not self.bearer_token:
            return False
        if not self.rate_limiter.is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/tweets/search/recent",
                    params={"query": "test", "max_results": 10},
                    headers={"Authorization": f"Bearer {self.bearer_token}"},
                )
                # 200 or 429 (rate limited) both indicate API is reachable
                return response.status_code in [200, 429]
        except Exception:
            return False

    async def fetch(self, **kwargs) -> list[Tweet]:
        """Fetch tweets."""
        return await self.search_recent(**kwargs)

    async def _search_recent_internal(
        self,
        query: str,
        max_results: int = 10,
        tweet_fields: list[str] | None = None,
    ) -> list[Tweet]:
        """Internal method to search recent tweets."""
        if tweet_fields is None:
            tweet_fields = ["created_at", "public_metrics", "author_id", "lang"]

        params = {
            "query": query,
            "max_results": max_results,
            "tweet.fields": ",".join(tweet_fields),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/tweets/search/recent",
                params=params,
                headers={"Authorization": f"Bearer {self.bearer_token}"},
            )
            response.raise_for_status()
            data = response.json()

        search_response = TwitterSearchResponse(**data)
        return search_response.data

    async def search_recent(
        self,
        query: str,
        max_results: int = 10,
        tweet_fields: list[str] | None = None,
    ) -> list[Tweet]:
        """Search recent tweets with rate limit handling."""
        result = await self.rate_limiter.execute(
            self._search_recent_internal,
            query=query,
            max_results=max_results,
            tweet_fields=tweet_fields,
            default=[],
        )
        return result or []

    async def _get_tweet_counts_internal(
        self,
        query: str,
        granularity: str = "hour",
    ) -> Optional[TwitterCountResponse]:
        """Internal method to get tweet counts."""
        params = {
            "query": query,
            "granularity": granularity,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                f"{self.BASE_URL}/tweets/counts/recent",
                params=params,
                headers={"Authorization": f"Bearer {self.bearer_token}"},
            )
            response.raise_for_status()
            data = response.json()

        return TwitterCountResponse(**data)

    async def get_tweet_counts(
        self,
        query: str,
        granularity: str = "hour",
    ) -> Optional[TwitterCountResponse]:
        """Get tweet counts with rate limit handling."""
        return await self.rate_limiter.execute(
            self._get_tweet_counts_internal,
            query=query,
            granularity=granularity,
            default=None,
        )


class MockSocialDataSource(DataSourceBase):
    """Mock Twitter/X data source for development."""

    # Mock tweets by topic
    MOCK_TWEETS = {
        "trump": [
            {"text": "Trump looking strong in the polls! 🇺🇸 #MAGA", "sentiment": 0.7, "likes": 1250, "retweets": 340},
            {"text": "Just watched Trump's rally - incredible energy", "sentiment": 0.6, "likes": 890, "retweets": 210},
            {"text": "Trump's economic policies will save this country", "sentiment": 0.5, "likes": 650, "retweets": 180},
            {"text": "Not sure about Trump's latest statements...", "sentiment": -0.2, "likes": 230, "retweets": 45},
            {"text": "Trump presidency would be a disaster for democracy", "sentiment": -0.8, "likes": 1100, "retweets": 420},
            {"text": "The polls are tightening for Trump", "sentiment": 0.0, "likes": 340, "retweets": 85},
        ],
        "harris": [
            {"text": "Harris crushing it in the debates! #Harris2024", "sentiment": 0.7, "likes": 980, "retweets": 290},
            {"text": "VP Harris just announced great new policy", "sentiment": 0.5, "likes": 560, "retweets": 140},
            {"text": "Harris campaign raising record amounts", "sentiment": 0.4, "likes": 420, "retweets": 95},
            {"text": "Harris needs to address border concerns", "sentiment": -0.3, "likes": 780, "retweets": 210},
            {"text": "Not convinced Harris can win swing states", "sentiment": -0.4, "likes": 340, "retweets": 70},
        ],
        "bitcoin": [
            {"text": "BTC to $100k is inevitable at this point 🚀", "sentiment": 0.9, "likes": 2100, "retweets": 580},
            {"text": "Just bought more Bitcoin. This is the way.", "sentiment": 0.7, "likes": 890, "retweets": 190},
            {"text": "Bitcoin ETF inflows are insane right now", "sentiment": 0.6, "likes": 1200, "retweets": 340},
            {"text": "BTC breaking out of the consolidation pattern", "sentiment": 0.5, "likes": 670, "retweets": 150},
            {"text": "Worried about Bitcoin's energy consumption", "sentiment": -0.3, "likes": 450, "retweets": 120},
            {"text": "Bitcoin is just speculation, not real value", "sentiment": -0.6, "likes": 320, "retweets": 80},
        ],
        "polymarket": [
            {"text": "Polymarket odds shifting big on the election", "sentiment": 0.0, "likes": 340, "retweets": 95},
            {"text": "Love using Polymarket for predictions", "sentiment": 0.5, "likes": 180, "retweets": 40},
            {"text": "Polymarket is the best prediction market", "sentiment": 0.6, "likes": 290, "retweets": 65},
        ],
        "default": [
            {"text": "Interesting market movements today", "sentiment": 0.0, "likes": 120, "retweets": 25},
            {"text": "Markets looking volatile", "sentiment": -0.1, "likes": 90, "retweets": 15},
        ],
    }

    def __init__(self):
        self._custom_mentions = {}  # Override mentions for specific markets
        self._mention_multiplier = {}  # Simulate spikes

    async def health_check(self) -> bool:
        """Mock always returns healthy."""
        return True

    async def fetch(self, **kwargs) -> list[Tweet]:
        """Fetch mock tweets."""
        return await self.search_recent(**kwargs)

    async def search_recent(
        self,
        query: str,
        max_results: int = 10,
        tweet_fields: list[str] | None = None,
    ) -> list[Tweet]:
        """Return mock tweets based on query."""
        query_lower = query.lower()
        tweets_data = []

        # Find matching tweets based on query keywords
        for topic, topic_tweets in self.MOCK_TWEETS.items():
            if topic in query_lower:
                tweets_data.extend(topic_tweets)

        # Fall back to default
        if not tweets_data:
            tweets_data = self.MOCK_TWEETS["default"]

        # Shuffle and limit
        random.shuffle(tweets_data)
        tweets_data = tweets_data[:max_results]

        # Convert to Tweet objects
        tweets = []
        for i, t in enumerate(tweets_data):
            tweet = Tweet(
                id=f"mock_tweet_{i}_{random.randint(1000, 9999)}",
                text=t["text"],
                author_id=f"user_{random.randint(100000, 999999)}",
                created_at=datetime.utcnow() - timedelta(hours=random.randint(1, 48)),
                public_metrics=TwitterPublicMetrics(
                    like_count=t["likes"] + random.randint(-50, 50),
                    retweet_count=t["retweets"] + random.randint(-20, 20),
                    reply_count=random.randint(10, 100),
                    quote_count=random.randint(5, 50),
                ),
                lang="en",
            )
            tweets.append(tweet)

        return tweets

    async def get_tweet_counts(
        self,
        query: str,
        granularity: str = "hour",
    ) -> TwitterCountResponse:
        """Return mock tweet counts."""
        query_lower = query.lower()

        # Base count depends on topic popularity
        base_count = 50
        for topic in ["trump", "harris", "bitcoin"]:
            if topic in query_lower:
                base_count = 200 + random.randint(0, 100)
                break

        # Check for spike multiplier
        for market_id, multiplier in self._mention_multiplier.items():
            if market_id in query_lower:
                base_count = int(base_count * multiplier)

        # Generate hourly buckets for last 24 hours
        buckets = []
        now = datetime.utcnow()

        hours = 24 if granularity == "hour" else 7
        for i in range(hours):
            if granularity == "hour":
                start = now - timedelta(hours=i + 1)
                end = now - timedelta(hours=i)
            else:
                start = now - timedelta(days=i + 1)
                end = now - timedelta(days=i)

            # Add variation
            count = base_count + random.randint(-base_count // 3, base_count // 3)
            count = max(0, count)

            buckets.append(
                TweetCountBucket(start=start, end=end, tweet_count=count)
            )

        total = sum(b.tweet_count for b in buckets)

        return TwitterCountResponse(
            data=buckets,
            meta={"total_tweet_count": total},
            total_tweet_count=total,
        )

    async def get_mentions_for_market(self, market_id: str, query: str) -> SocialMention:
        """Get aggregated social mention data for a market."""
        # Check for custom override
        if market_id in self._custom_mentions:
            return self._custom_mentions[market_id]

        # Get counts
        hourly_counts = await self.get_tweet_counts(query, granularity="hour")

        # Calculate metrics
        mention_1h = hourly_counts.data[0].tweet_count if hourly_counts.data else 0
        mention_24h = sum(b.tweet_count for b in hourly_counts.data[:24])

        # Get sample tweets for engagement metrics
        tweets = await self.search_recent(query, max_results=20)
        total_likes = sum(t.public_metrics.like_count for t in tweets if t.public_metrics)
        total_retweets = sum(t.public_metrics.retweet_count for t in tweets if t.public_metrics)
        total_replies = sum(t.public_metrics.reply_count for t in tweets if t.public_metrics)

        # Calculate velocity (mentions per hour)
        velocity = mention_24h / 24

        # Estimate 7d count
        mention_7d = mention_24h * 7 + random.randint(-mention_24h, mention_24h)

        return SocialMention(
            market_id=market_id,
            platform="twitter",
            mention_count_1h=mention_1h,
            mention_count_24h=mention_24h,
            mention_count_7d=mention_7d,
            total_likes=total_likes,
            total_retweets=total_retweets,
            total_replies=total_replies,
            mention_velocity=round(velocity, 2),
            velocity_change_pct=random.uniform(-20, 20),
            top_tweet_ids=[t.id for t in tweets[:5]],
        )

    async def get_sentiment_for_market(self, market_id: str, query: str) -> SocialSentiment:
        """Get social sentiment for a market."""
        tweets = await self.search_recent(query, max_results=30)

        # Calculate sentiment from mock data
        query_lower = query.lower()
        sentiments = []

        for topic, topic_tweets in self.MOCK_TWEETS.items():
            if topic in query_lower:
                for t in topic_tweets:
                    sentiments.append(t["sentiment"])

        if not sentiments:
            sentiments = [random.uniform(-0.2, 0.2) for _ in range(10)]

        avg_sentiment = sum(sentiments) / len(sentiments)
        avg_sentiment += random.uniform(-0.1, 0.1)
        avg_sentiment = max(-1.0, min(1.0, avg_sentiment))

        positive = len([s for s in sentiments if s > 0.2])
        negative = len([s for s in sentiments if s < -0.2])
        neutral = len(sentiments) - positive - negative
        total = len(sentiments)

        return SocialSentiment(
            market_id=market_id,
            platform="twitter",
            sentiment_score=round(avg_sentiment, 2),
            confidence=min(1.0, len(tweets) / 20),
            positive_pct=round(positive / total * 100, 1) if total else 0,
            negative_pct=round(negative / total * 100, 1) if total else 0,
            neutral_pct=round(neutral / total * 100, 1) if total else 0,
            posts_analyzed=len(tweets),
        )

    def set_mention_spike(self, market_id: str, multiplier: float) -> None:
        """Simulate a mention spike for testing signal generation."""
        self._mention_multiplier[market_id] = multiplier

    def clear_mention_spike(self, market_id: str) -> None:
        """Clear mention spike."""
        if market_id in self._mention_multiplier:
            del self._mention_multiplier[market_id]
