"""Social media models matching Twitter/X API v2 structure."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TwitterUser(BaseModel):
    """Twitter user object from API v2."""

    id: str
    name: str
    username: str


class TwitterPublicMetrics(BaseModel):
    """Public metrics for a tweet."""

    retweet_count: int = 0
    reply_count: int = 0
    like_count: int = 0
    quote_count: int = 0
    bookmark_count: int = 0
    impression_count: int = 0


class Tweet(BaseModel):
    """
    Tweet model matching Twitter API v2 structure.

    Based on: https://developer.twitter.com/en/docs/twitter-api/tweets/search/api-reference
    """

    id: str
    text: str
    author_id: Optional[str] = None
    created_at: Optional[datetime] = None
    public_metrics: Optional[TwitterPublicMetrics] = None
    lang: Optional[str] = None

    # Expansions (if requested)
    author: Optional[TwitterUser] = None


class TwitterSearchResponse(BaseModel):
    """Response from Twitter search endpoint."""

    data: list[Tweet] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    includes: Optional[dict] = None


class TweetCountBucket(BaseModel):
    """Tweet count for a time bucket."""

    start: datetime
    end: datetime
    tweet_count: int


class TwitterCountResponse(BaseModel):
    """Response from Twitter counts endpoint."""

    data: list[TweetCountBucket] = Field(default_factory=list)
    meta: dict = Field(default_factory=dict)
    total_tweet_count: int = 0


class SocialMention(BaseModel):
    """
    Aggregated social mention data for a market.

    Tracks mentions and engagement across social platforms.
    """

    market_id: str
    platform: str = "twitter"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Mention counts
    mention_count_1h: int = 0
    mention_count_24h: int = 0
    mention_count_7d: int = 0

    # Engagement metrics
    total_likes: int = 0
    total_retweets: int = 0
    total_replies: int = 0

    # Velocity (rate of change)
    mention_velocity: float = Field(
        default=0.0, description="Mentions per hour, normalized"
    )
    velocity_change_pct: float = Field(
        default=0.0, description="Change in velocity vs previous period"
    )

    # Top tweets
    top_tweet_ids: list[str] = Field(default_factory=list)


class SocialSentiment(BaseModel):
    """
    Social sentiment analysis for a market.

    Computed from recent social media posts.
    """

    market_id: str
    platform: str = "twitter"
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Sentiment
    sentiment_score: float = Field(
        ge=-1.0, le=1.0, description="Aggregate sentiment -1.0 to 1.0"
    )
    confidence: float = Field(ge=0.0, le=1.0)

    # Breakdown
    positive_pct: float = 0.0
    negative_pct: float = 0.0
    neutral_pct: float = 0.0

    # Sample size
    posts_analyzed: int = 0


class SocialAlert(BaseModel):
    """Alert triggered by social activity spike."""

    market_id: str
    timestamp: datetime
    alert_type: str  # "spike", "viral_post", "sentiment_shift"
    description: str
    magnitude: float  # How significant the change is
