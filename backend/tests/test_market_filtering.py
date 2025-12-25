"""Tests for market filtering functionality."""

import pytest
from datetime import datetime, timedelta, timezone

from src.models.market import Market, MarketTier
from src.services.data_sources.polymarket import (
    is_market_current,
    MockPolymarketDataSource,
)


class TestIsMarketCurrent:
    """Test the is_market_current filtering function."""

    def test_accepts_open_active_market(self):
        """Should return True for open, active markets."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=False,
            accepting_orders=True,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
            end_date=datetime.now(timezone.utc) + timedelta(days=30),
        )

        assert is_market_current(market) is True

    def test_rejects_closed_market(self):
        """Should return False for closed markets."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=True,  # Closed
            archived=False,
            accepting_orders=False,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
        )

        assert is_market_current(market) is False

    def test_rejects_archived_market(self):
        """Should return False for archived markets."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=True,  # Archived
            accepting_orders=False,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
        )

        assert is_market_current(market) is False

    def test_rejects_not_accepting_orders(self):
        """Should return False for markets not accepting orders."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=False,
            accepting_orders=False,  # Not accepting orders
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
        )

        assert is_market_current(market) is False

    def test_rejects_expired_market(self):
        """Should return False for markets past their end_date."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=False,
            accepting_orders=True,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
            end_date=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
        )

        assert is_market_current(market) is False

    def test_handles_timezone_naive_dates(self):
        """Should handle timezone-naive end_dates correctly."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=False,
            accepting_orders=True,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
            end_date=datetime.utcnow() - timedelta(days=1),  # Naive datetime in past
        )

        assert is_market_current(market) is False

    def test_accepts_market_without_end_date(self):
        """Should return True for markets without an end_date (if other conditions met)."""
        market = Market(
            id="test-1",
            condition_id="0x123",
            question="Test market?",
            active=True,
            closed=False,
            archived=False,
            accepting_orders=True,
            volume=100_000,
            volume_24h=10_000,
            liquidity=50_000,
            current_price=0.50,
            tier=MarketTier.MEDIUM,
            end_date=None,  # No end date
        )

        assert is_market_current(market) is True


class TestMockPolymarketDataSourceFiltering:
    """Test that MockPolymarketDataSource properly filters markets."""

    @pytest.mark.asyncio
    async def test_filter_current_removes_closed_markets(self):
        """Should filter out closed markets when filter_current=True."""
        mock_source = MockPolymarketDataSource()

        # Add a closed market
        mock_source.add_mock_market({
            "id": "closed-market",
            "condition_id": "0xCLOSED",
            "question": "Closed market?",
            "slug": "closed-market",
            "category": "Test",
            "active": True,
            "closed": True,  # Closed
            "volume": 100_000,
            "volume_24h": 1_000,
            "liquidity": 50_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.50, 0.50]",
            "end_date": "2024-01-01T00:00:00Z",
        })

        # Get markets with filtering enabled
        markets_filtered = await mock_source.get_markets(filter_current=True)
        market_ids_filtered = {m.id for m in markets_filtered}

        # Get markets without filtering
        markets_unfiltered = await mock_source.get_markets(filter_current=False)
        market_ids_unfiltered = {m.id for m in markets_unfiltered}

        # Closed market should be in unfiltered but not in filtered
        assert "closed-market" not in market_ids_filtered
        assert "closed-market" in market_ids_unfiltered

    @pytest.mark.asyncio
    async def test_filter_current_removes_archived_markets(self):
        """Should filter out archived markets when filter_current=True."""
        mock_source = MockPolymarketDataSource()

        # Add an archived market
        mock_source.add_mock_market({
            "id": "archived-market",
            "condition_id": "0xARCHIVED",
            "question": "Archived market?",
            "slug": "archived-market",
            "category": "Test",
            "active": False,
            "closed": False,
            "archived": True,  # Archived
            "volume": 100_000,
            "volume_24h": 1_000,
            "liquidity": 50_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.50, 0.50]",
            "end_date": "2025-12-31T00:00:00Z",
        })

        # Get markets with filtering enabled
        markets_filtered = await mock_source.get_markets(filter_current=True)
        market_ids_filtered = {m.id for m in markets_filtered}

        # Get markets without filtering
        markets_unfiltered = await mock_source.get_markets(filter_current=False)
        market_ids_unfiltered = {m.id for m in markets_unfiltered}

        # Archived market should be in unfiltered but not in filtered
        assert "archived-market" not in market_ids_filtered
        assert "archived-market" in market_ids_unfiltered

    @pytest.mark.asyncio
    async def test_default_filter_current_is_true(self):
        """Should filter by default when filter_current is not specified."""
        mock_source = MockPolymarketDataSource()

        # Add a closed market
        mock_source.add_mock_market({
            "id": "closed-default-test",
            "condition_id": "0xCLOSED2",
            "question": "Closed market for default test?",
            "slug": "closed-default",
            "category": "Test",
            "active": True,
            "closed": True,  # Closed
            "volume": 100_000,
            "volume_24h": 1_000,
            "liquidity": 50_000,
            "outcomes": ["Yes", "No"],
            "outcome_prices": "[0.50, 0.50]",
            "end_date": "2024-01-01T00:00:00Z",
        })

        # Get markets without specifying filter_current (should default to True)
        markets = await mock_source.get_markets()
        market_ids = {m.id for m in markets}

        # Closed market should not be in results (filtered by default)
        assert "closed-default-test" not in market_ids
