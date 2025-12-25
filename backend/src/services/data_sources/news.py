"""News data source with real (NewsAPI) and mock implementations."""

import logging
import random
from datetime import datetime, timedelta
from typing import Optional

import httpx

from src.config import get_settings
from src.models.news import NewsArticle, NewsAPIResponse, NewsSentiment, NewsSource
from src.services.data_sources.base import DataSourceBase
from src.services.data_sources.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)


class NewsDataSource(DataSourceBase):
    """Real NewsAPI data source."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.newsapi_key
        self.timeout = 30.0
        self.rate_limiter = get_rate_limiter("newsapi")

    async def health_check(self) -> bool:
        """Check if NewsAPI is available."""
        if not self.api_key:
            return False
        if not self.rate_limiter.is_available():
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/top-headlines",
                    params={"apiKey": self.api_key, "country": "us", "pageSize": 1},
                )
                return response.status_code == 200
        except Exception:
            return False

    async def fetch(self, **kwargs) -> list[NewsArticle]:
        """Fetch news articles."""
        return await self.search_news(**kwargs)

    async def _search_news_internal(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Internal method to search news articles."""
        params = {
            "apiKey": self.api_key,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": page_size,
        }

        if from_date:
            params["from"] = from_date.isoformat()
        if to_date:
            params["to"] = to_date.isoformat()

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/everything", params=params)
            response.raise_for_status()
            data = response.json()

        api_response = NewsAPIResponse(**data)
        return api_response.articles

    async def search_news(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Search news articles with rate limit handling."""
        result = await self.rate_limiter.execute(
            self._search_news_internal,
            query=query,
            from_date=from_date,
            to_date=to_date,
            language=language,
            sort_by=sort_by,
            page_size=page_size,
            default=[],
        )
        return result or []

    async def _get_top_headlines_internal(
        self,
        category: Optional[str] = None,
        country: str = "us",
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Internal method to get top headlines."""
        params = {
            "apiKey": self.api_key,
            "country": country,
            "pageSize": page_size,
        }

        if category:
            params["category"] = category

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.BASE_URL}/top-headlines", params=params)
            response.raise_for_status()
            data = response.json()

        api_response = NewsAPIResponse(**data)
        return api_response.articles

    async def get_top_headlines(
        self,
        category: Optional[str] = None,
        country: str = "us",
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Get top headlines with rate limit handling."""
        result = await self.rate_limiter.execute(
            self._get_top_headlines_internal,
            category=category,
            country=country,
            page_size=page_size,
            default=[],
        )
        return result or []


class MockNewsDataSource(DataSourceBase):
    """Mock news data source for development."""

    # Mock news headlines keyed by topic
    MOCK_HEADLINES = {
        "trump": [
            {
                "title": "Trump Leads in Key Battleground State Polls",
                "description": "New polling shows former president with 3-point lead in Pennsylvania",
                "source": "Reuters",
                "sentiment": 0.6,
            },
            {
                "title": "Trump Rally Draws Record Crowd in Michigan",
                "description": "Campaign claims 50,000 attendees at Detroit event",
                "source": "AP News",
                "sentiment": 0.5,
            },
            {
                "title": "Trump Campaign Announces Major Ad Buy in Swing States",
                "description": "$100M advertising campaign targets undecided voters",
                "source": "Politico",
                "sentiment": 0.4,
            },
            {
                "title": "Former Officials Criticize Trump Policy Proposals",
                "description": "National security experts express concerns over foreign policy plans",
                "source": "Washington Post",
                "sentiment": -0.5,
            },
            {
                "title": "Trump Faces Legal Setback in Federal Case",
                "description": "Judge denies motion to dismiss charges",
                "source": "CNN",
                "sentiment": -0.6,
            },
        ],
        "harris": [
            {
                "title": "Harris Campaign Reports Strong Fundraising Quarter",
                "description": "Vice President's campaign raises $200M in Q3",
                "source": "NYT",
                "sentiment": 0.6,
            },
            {
                "title": "Harris Outlines Economic Policy in Major Speech",
                "description": "Focus on middle class tax relief and housing affordability",
                "source": "Bloomberg",
                "sentiment": 0.4,
            },
            {
                "title": "Harris Gains Ground with Independent Voters",
                "description": "New polls show improved standing among key demographic",
                "source": "FiveThirtyEight",
                "sentiment": 0.5,
            },
            {
                "title": "Harris Debate Performance Receives Mixed Reviews",
                "description": "Analysts divided on impact of town hall appearance",
                "source": "NBC News",
                "sentiment": 0.0,
            },
            {
                "title": "Critics Question Harris Border Record",
                "description": "Opposition highlights immigration challenges",
                "source": "Fox News",
                "sentiment": -0.5,
            },
        ],
        "bitcoin": [
            {
                "title": "Bitcoin Surges Past $95,000 on ETF Inflows",
                "description": "Institutional buying drives cryptocurrency to new highs",
                "source": "CoinDesk",
                "sentiment": 0.8,
            },
            {
                "title": "Major Bank Launches Bitcoin Custody Service",
                "description": "Wall Street giant enters crypto custody market",
                "source": "Bloomberg",
                "sentiment": 0.6,
            },
            {
                "title": "Bitcoin Mining Difficulty Reaches All-Time High",
                "description": "Network hash rate continues upward trend",
                "source": "The Block",
                "sentiment": 0.3,
            },
            {
                "title": "Regulatory Concerns Weigh on Crypto Markets",
                "description": "SEC signals increased scrutiny of digital assets",
                "source": "Reuters",
                "sentiment": -0.4,
            },
        ],
        "federal reserve": [
            {
                "title": "Fed Officials Signal Patience on Rate Cuts",
                "description": "Minutes show divided committee on timing of easing",
                "source": "WSJ",
                "sentiment": -0.3,
            },
            {
                "title": "Inflation Data Supports Case for Steady Rates",
                "description": "Core PCE remains above Fed target",
                "source": "CNBC",
                "sentiment": -0.2,
            },
            {
                "title": "Powell Hints at Possible January Rate Decision",
                "description": "Chair's comments spark market speculation",
                "source": "Financial Times",
                "sentiment": 0.4,
            },
        ],
        "default": [
            {
                "title": "Markets Rally on Economic Optimism",
                "description": "S&P 500 reaches new record high",
                "source": "Bloomberg",
                "sentiment": 0.5,
            },
            {
                "title": "Analysts Predict Strong Holiday Shopping Season",
                "description": "Consumer spending expected to rise 4% year-over-year",
                "source": "Reuters",
                "sentiment": 0.4,
            },
        ],
    }

    def __init__(self):
        self._custom_sentiment = {}  # Override sentiment for specific markets

    async def health_check(self) -> bool:
        """Mock always returns healthy."""
        return True

    async def fetch(self, **kwargs) -> list[NewsArticle]:
        """Fetch mock news articles."""
        return await self.search_news(**kwargs)

    async def search_news(
        self,
        query: str,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        language: str = "en",
        sort_by: str = "relevancy",
        page_size: int = 20,
    ) -> list[NewsArticle]:
        """Return mock news articles based on query."""
        # Find matching headlines based on query keywords
        query_lower = query.lower()
        headlines = []

        for topic, topic_headlines in self.MOCK_HEADLINES.items():
            if topic in query_lower:
                headlines.extend(topic_headlines)

        # Fall back to default headlines if no match
        if not headlines:
            headlines = self.MOCK_HEADLINES["default"]

        # Shuffle and limit
        random.shuffle(headlines)
        headlines = headlines[:page_size]

        # Convert to NewsArticle objects with realistic timestamps
        articles = []
        for i, h in enumerate(headlines):
            # Stagger publication times
            pub_time = datetime.utcnow() - timedelta(hours=random.randint(1, 72))

            article = NewsArticle(
                source=NewsSource(id=h["source"].lower().replace(" ", "-"), name=h["source"]),
                author=f"Staff Writer",
                title=h["title"],
                description=h["description"],
                url=f"https://example.com/news/{i}",
                urlToImage=f"https://example.com/images/{i}.jpg",
                publishedAt=pub_time,
                content=h["description"],
            )
            articles.append(article)

        return articles

    async def get_sentiment_for_market(self, market_id: str, query: str) -> NewsSentiment:
        """Get aggregated news sentiment for a market."""
        # Check for custom override
        if market_id in self._custom_sentiment:
            return self._custom_sentiment[market_id]

        # Get articles and compute sentiment
        articles = await self.search_news(query=query, page_size=10)

        # Find matching headlines to get sentiment
        query_lower = query.lower()
        sentiments = []

        for topic, topic_headlines in self.MOCK_HEADLINES.items():
            if topic in query_lower:
                for h in topic_headlines:
                    sentiments.append(h["sentiment"])

        if not sentiments:
            # Random neutral-ish sentiment
            sentiments = [random.uniform(-0.2, 0.2) for _ in range(5)]

        avg_sentiment = sum(sentiments) / len(sentiments)

        # Add some noise
        avg_sentiment += random.uniform(-0.1, 0.1)
        avg_sentiment = max(-1.0, min(1.0, avg_sentiment))

        positive = len([s for s in sentiments if s > 0.2])
        negative = len([s for s in sentiments if s < -0.2])
        neutral = len(sentiments) - positive - negative

        return NewsSentiment(
            market_id=market_id,
            sentiment_score=round(avg_sentiment, 2),
            confidence=min(1.0, len(articles) / 10),
            article_count=len(articles),
            positive_count=positive,
            negative_count=negative,
            neutral_count=neutral,
            top_headlines=[a.title for a in articles[:5]],
            sources=list(set(a.source.name for a in articles)),
        )

    def set_sentiment(self, market_id: str, sentiment: NewsSentiment) -> None:
        """Set custom sentiment for testing signal generation."""
        self._custom_sentiment[market_id] = sentiment
