"""News models matching NewsAPI structure."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class NewsSource(BaseModel):
    """News source from NewsAPI."""

    id: Optional[str] = None
    name: str


class NewsArticle(BaseModel):
    """
    News article model matching NewsAPI structure.

    Based on: https://newsapi.org/docs/endpoints/everything
    """

    source: NewsSource
    author: Optional[str] = None
    title: str
    description: Optional[str] = None
    url: str
    url_to_image: Optional[str] = Field(default=None, alias="urlToImage")
    published_at: datetime = Field(alias="publishedAt")
    content: Optional[str] = None

    class Config:
        populate_by_name = True


class NewsAPIResponse(BaseModel):
    """Response structure from NewsAPI."""

    status: str
    total_results: int = Field(alias="totalResults")
    articles: list[NewsArticle]

    class Config:
        populate_by_name = True


class NewsSentiment(BaseModel):
    """
    Aggregated news sentiment for a market.

    Computed from recent news articles related to the market.
    """

    market_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Sentiment scores
    sentiment_score: float = Field(
        ge=-1.0, le=1.0, description="Aggregate sentiment -1.0 (negative) to 1.0 (positive)"
    )
    confidence: float = Field(
        ge=0.0, le=1.0, description="Confidence in sentiment score based on article count"
    )

    # Article stats
    article_count: int = Field(description="Number of articles analyzed")
    positive_count: int = Field(default=0)
    negative_count: int = Field(default=0)
    neutral_count: int = Field(default=0)

    # Top headlines
    top_headlines: list[str] = Field(
        default_factory=list, description="Most relevant headlines"
    )

    # Source breakdown
    sources: list[str] = Field(default_factory=list, description="News sources used")


class NewsSentimentHistory(BaseModel):
    """Historical sentiment data point for tracking trends."""

    market_id: str
    timestamp: datetime
    sentiment_score: float
    article_count: int
