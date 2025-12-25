"""Supabase client wrapper for database operations."""

from functools import lru_cache
from typing import Any, Optional
from uuid import UUID

from supabase import create_client, Client

from src.config import get_settings
from src.models.market import Market, MarketTier
from src.models.signal import Signal, SignalStatus, SignalStats


class SupabaseClient:
    """Wrapper around Supabase client with typed methods."""

    def __init__(self, client: Client):
        self._client = client

    # ==========================================
    # MARKET OPERATIONS
    # ==========================================

    async def upsert_market(self, market: Market) -> Market:
        """Insert or update a market."""
        data = market.model_dump(exclude_none=True, by_alias=False)
        # Convert enum to string
        if market.tier:
            data["tier"] = market.tier.value

        result = self._client.table("markets").upsert(data).execute()
        return Market(**result.data[0]) if result.data else market

    async def upsert_markets(self, markets: list[Market]) -> int:
        """Bulk upsert markets. Returns count of upserted rows."""
        if not markets:
            return 0

        data = []
        for market in markets:
            m = market.model_dump(exclude_none=True, by_alias=False)
            if market.tier:
                m["tier"] = market.tier.value
            data.append(m)

        result = self._client.table("markets").upsert(data).execute()
        return len(result.data) if result.data else 0

    async def get_market(self, market_id: str) -> Optional[Market]:
        """Get a market by ID."""
        result = self._client.table("markets").select("*").eq("id", market_id).execute()
        if result.data:
            return Market(**result.data[0])
        return None

    async def get_market_by_slug(self, slug: str) -> Optional[Market]:
        """Get a market by slug."""
        result = self._client.table("markets").select("*").eq("slug", slug).execute()
        if result.data:
            return Market(**result.data[0])
        return None

    async def get_markets(
        self,
        tier: Optional[MarketTier] = None,
        active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Market]:
        """Get markets with optional filters."""
        query = self._client.table("markets").select("*")

        if tier:
            query = query.eq("tier", tier.value)
        if active is not None:
            query = query.eq("active", active)

        query = query.order("volume", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return [Market(**m) for m in result.data] if result.data else []

    # ==========================================
    # SIGNAL OPERATIONS
    # ==========================================

    async def create_signal(self, signal: Signal) -> Signal:
        """Create a new signal."""
        data = signal.model_dump(exclude_none=True)
        # Convert enums to strings
        data["id"] = str(data["id"])
        data["signal_type"] = signal.signal_type.value
        data["direction"] = signal.direction.value
        data["status"] = signal.status.value
        data["market_tier"] = signal.market_tier.value

        # Handle datetime serialization
        for key in ["created_at", "market_end_date", "resolved_at"]:
            if key in data and data[key]:
                data[key] = data[key].isoformat()

        result = self._client.table("signals").insert(data).execute()
        return Signal(**result.data[0]) if result.data else signal

    async def get_signal(self, signal_id: UUID) -> Optional[Signal]:
        """Get a signal by ID."""
        result = (
            self._client.table("signals")
            .select("*")
            .eq("id", str(signal_id))
            .execute()
        )
        if result.data:
            return Signal(**result.data[0])
        return None

    async def get_signals(
        self,
        status: Optional[SignalStatus] = None,
        signal_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Signal]:
        """Get signals with optional filters."""
        query = self._client.table("signals").select("*")

        if status:
            query = query.eq("status", status.value)
        if signal_type:
            query = query.eq("signal_type", signal_type)

        query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
        result = query.execute()

        return [Signal(**s) for s in result.data] if result.data else []

    async def get_active_signals(self) -> list[Signal]:
        """Get all active signals."""
        return await self.get_signals(status=SignalStatus.ACTIVE, limit=100)

    async def update_signal(self, signal: Signal) -> Signal:
        """Update an existing signal."""
        data = {
            "price_1h": signal.price_1h,
            "price_24h": signal.price_24h,
            "price_7d": signal.price_7d,
            "price_at_resolution": signal.price_at_resolution,
            "gain_1h_pct": signal.gain_1h_pct,
            "gain_24h_pct": signal.gain_24h_pct,
            "gain_7d_pct": signal.gain_7d_pct,
            "gain_final_pct": signal.gain_final_pct,
            "status": signal.status.value,
        }

        if signal.resolved_at:
            data["resolved_at"] = signal.resolved_at.isoformat()

        # Remove None values
        data = {k: v for k, v in data.items() if v is not None}

        result = (
            self._client.table("signals")
            .update(data)
            .eq("id", str(signal.id))
            .execute()
        )
        return Signal(**result.data[0]) if result.data else signal

    async def get_signal_stats(self) -> SignalStats:
        """Get aggregate signal statistics."""
        result = self._client.table("signal_stats").select("*").execute()

        if result.data:
            row = result.data[0]
            return SignalStats(
                total_signals=row.get("total_signals") or 0,
                active_signals=row.get("active_signals") or 0,
                resolved_signals=row.get("resolved_signals") or 0,
                wins=row.get("wins") or 0,
                losses=row.get("losses") or 0,
                win_rate=row.get("win_rate_pct") or 0.0,
                avg_gain_pct=row.get("avg_gain_pct") or 0.0,
                best_gain_pct=row.get("best_gain_pct") or 0.0,
                worst_gain_pct=row.get("worst_gain_pct") or 0.0,
            )
        return SignalStats()

    async def get_signal_stats_by_type(self) -> dict[str, dict]:
        """Get signal stats grouped by type."""
        result = self._client.table("signal_stats_by_type").select("*").execute()

        stats = {}
        if result.data:
            for row in result.data:
                stats[row["signal_type"]] = {
                    "total_signals": row.get("total_signals") or 0,
                    "wins": row.get("wins") or 0,
                    "losses": row.get("losses") or 0,
                    "win_rate": row.get("win_rate_pct") or 0.0,
                    "avg_gain_pct": row.get("avg_gain_pct") or 0.0,
                }
        return stats

    # ==========================================
    # SENTIMENT OPERATIONS
    # ==========================================

    async def save_news_sentiment(
        self,
        market_id: str,
        sentiment_score: float,
        confidence: float,
        article_count: int,
        positive_count: int = 0,
        negative_count: int = 0,
        neutral_count: int = 0,
        top_headlines: list[str] | None = None,
        sources: list[str] | None = None,
    ) -> None:
        """Save news sentiment for a market."""
        data = {
            "market_id": market_id,
            "sentiment_score": sentiment_score,
            "confidence": confidence,
            "article_count": article_count,
            "positive_count": positive_count,
            "negative_count": negative_count,
            "neutral_count": neutral_count,
            "top_headlines": top_headlines or [],
            "sources": sources or [],
        }
        self._client.table("news_sentiment").insert(data).execute()

    async def get_latest_news_sentiment(self, market_id: str) -> Optional[dict]:
        """Get most recent news sentiment for a market."""
        result = (
            self._client.table("news_sentiment")
            .select("*")
            .eq("market_id", market_id)
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def save_social_mentions(
        self,
        market_id: str,
        mention_count_1h: int,
        mention_count_24h: int,
        mention_count_7d: int,
        total_likes: int = 0,
        total_retweets: int = 0,
        total_replies: int = 0,
        mention_velocity: float = 0,
        velocity_change_pct: float = 0,
        top_tweet_ids: list[str] | None = None,
    ) -> None:
        """Save social mention data for a market."""
        data = {
            "market_id": market_id,
            "mention_count_1h": mention_count_1h,
            "mention_count_24h": mention_count_24h,
            "mention_count_7d": mention_count_7d,
            "total_likes": total_likes,
            "total_retweets": total_retweets,
            "total_replies": total_replies,
            "mention_velocity": mention_velocity,
            "velocity_change_pct": velocity_change_pct,
            "top_tweet_ids": top_tweet_ids or [],
        }
        self._client.table("social_mentions").insert(data).execute()

    async def get_latest_social_mentions(self, market_id: str) -> Optional[dict]:
        """Get most recent social mention data for a market."""
        result = (
            self._client.table("social_mentions")
            .select("*")
            .eq("market_id", market_id)
            .order("recorded_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    # ==========================================
    # USER OPERATIONS
    # ==========================================

    async def get_profile(self, user_id: UUID) -> Optional[dict]:
        """Get user profile."""
        result = (
            self._client.table("profiles")
            .select("*")
            .eq("id", str(user_id))
            .execute()
        )
        return result.data[0] if result.data else None

    async def update_alert_preferences(
        self, user_id: UUID, preferences: dict
    ) -> None:
        """Update user alert preferences."""
        self._client.table("profiles").update(
            {"alert_preferences": preferences}
        ).eq("id", str(user_id)).execute()

    async def follow_signal(
        self,
        user_id: UUID,
        signal_id: UUID,
        entry_price_actual: Optional[float] = None,
        notes: Optional[str] = None,
    ) -> None:
        """Record that a user followed a signal."""
        data = {
            "user_id": str(user_id),
            "signal_id": str(signal_id),
            "entry_price_actual": entry_price_actual,
            "notes": notes,
        }
        self._client.table("user_signal_follows").insert(data).execute()

    async def get_user_follows(self, user_id: UUID) -> list[dict]:
        """Get all signals a user has followed."""
        result = (
            self._client.table("user_signal_follows")
            .select("*, signals(*)")
            .eq("user_id", str(user_id))
            .order("followed_at", desc=True)
            .execute()
        )
        return result.data if result.data else []


@lru_cache
def get_supabase_client() -> SupabaseClient:
    """Get cached Supabase client instance using service role key for backend operations."""
    settings = get_settings()
    # Use service role key to bypass RLS for backend write operations
    key = settings.supabase_service_role_key or settings.supabase_anon_key
    client = create_client(settings.supabase_url, key)
    return SupabaseClient(client)
