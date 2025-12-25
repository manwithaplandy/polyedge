'use client';

import { useEffect, useState, useCallback } from 'react';
import { MarketCard, MarketCardSkeleton } from '@/components/markets/MarketCard';
import { marketsApi } from '@/lib/api';
import type { Market, MarketTier } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const MARKET_TIERS: { value: MarketTier | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All Tiers' },
  { value: 'HIGH', label: 'High Volume' },
  { value: 'MEDIUM', label: 'Medium' },
  { value: 'LOW', label: 'Low' },
  { value: 'THIN', label: 'Thin' },
];

const PAGE_SIZE = 12;

export default function MarketsPage() {
  const [markets, setMarkets] = useState<Market[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [tierFilter, setTierFilter] = useState<MarketTier | 'ALL'>('ALL');
  const [showActiveOnly, setShowActiveOnly] = useState(false);

  const fetchMarkets = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number | boolean> = {
        limit: PAGE_SIZE,
        offset,
      };

      if (tierFilter !== 'ALL') {
        params.tier = tierFilter;
      }
      if (showActiveOnly) {
        params.has_active_signal = true;
      }

      const data = await marketsApi.list(params);
      setMarkets(data.markets);
      setTotal(data.total);
    } catch (err) {
      setError('Failed to load markets');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [offset, tierFilter, showActiveOnly]);

  useEffect(() => {
    fetchMarkets();
  }, [fetchMarkets]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [tierFilter, showActiveOnly]);

  const hasMore = offset + PAGE_SIZE < total;
  const hasPrev = offset > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Markets</h1>
        <p className="text-zinc-400 mt-1">
          Browse Polymarket prediction markets we&apos;re tracking.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        {/* Tier Filter */}
        <div className="flex flex-wrap gap-2">
          {MARKET_TIERS.map((tier) => (
            <Button
              key={tier.value}
              variant="outline"
              size="sm"
              onClick={() => setTierFilter(tier.value)}
              className={cn(
                "border-zinc-700",
                tierFilter === tier.value
                  ? "bg-zinc-700 text-white border-zinc-600"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              )}
            >
              {tier.label}
            </Button>
          ))}
        </div>

        {/* Active Signal Toggle */}
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowActiveOnly(!showActiveOnly)}
          className={cn(
            "border-zinc-700",
            showActiveOnly
              ? "bg-emerald-500/20 text-emerald-500 border-emerald-500/50"
              : "text-zinc-400 hover:text-white hover:bg-zinc-800"
          )}
        >
          {showActiveOnly ? 'Showing Active Signals' : 'Show Active Signals Only'}
        </Button>
      </div>

      {/* Results Summary */}
      <div className="text-sm text-zinc-500">
        {!loading && (
          <>
            Showing {markets.length > 0 ? offset + 1 : 0}-{Math.min(offset + PAGE_SIZE, total)} of {total} markets
          </>
        )}
      </div>

      {/* Market Grid */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <MarketCardSkeleton key={i} />
          ))}
        </div>
      ) : error ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="py-8 text-center">
            <p className="text-red-500">{error}</p>
            <Button
              onClick={fetchMarkets}
              variant="outline"
              className="mt-4 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Try Again
            </Button>
          </CardContent>
        </Card>
      ) : markets.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="py-8 text-center">
            <p className="text-zinc-400">No markets found with the current filters.</p>
            <Button
              onClick={() => {
                setTierFilter('ALL');
                setShowActiveOnly(false);
              }}
              variant="outline"
              className="mt-4 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Clear Filters
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {markets.map((market) => (
            <MarketCard key={market.id} market={market} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && markets.length > 0 && (hasPrev || hasMore) && (
        <div className="flex items-center justify-center gap-4 pt-4">
          <Button
            variant="outline"
            onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            disabled={!hasPrev}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            Previous
          </Button>
          <span className="text-zinc-500 text-sm">
            Page {Math.floor(offset / PAGE_SIZE) + 1} of {Math.ceil(total / PAGE_SIZE)}
          </span>
          <Button
            variant="outline"
            onClick={() => setOffset(offset + PAGE_SIZE)}
            disabled={!hasMore}
            className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
          >
            Next
          </Button>
        </div>
      )}

      {/* Tier Legend */}
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-4">
          <h3 className="text-sm font-medium text-white mb-3">Volume Tiers</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-emerald-500 font-medium">HIGH</span>
              <span className="text-zinc-500 ml-2">&gt; $95K volume</span>
            </div>
            <div>
              <span className="text-blue-500 font-medium">MEDIUM</span>
              <span className="text-zinc-500 ml-2">$27K - $95K</span>
            </div>
            <div>
              <span className="text-yellow-500 font-medium">LOW</span>
              <span className="text-zinc-500 ml-2">$10K - $27K</span>
            </div>
            <div>
              <span className="text-zinc-400 font-medium">THIN</span>
              <span className="text-zinc-500 ml-2">&lt; $10K volume</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
