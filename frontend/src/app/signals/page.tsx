'use client';

import { useEffect, useState, useCallback } from 'react';
import { SignalCard } from '@/components/signals/SignalCard';
import { signalsApi } from '@/lib/api';
import type { Signal, SignalStatus, SignalType } from '@/types';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

const SIGNAL_STATUSES: { value: SignalStatus | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All Signals' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'RESOLVED_WIN', label: 'Wins' },
  { value: 'RESOLVED_LOSS', label: 'Losses' },
  { value: 'EXPIRED', label: 'Expired' },
];

const SIGNAL_TYPES: { value: SignalType | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All Types' },
  { value: 'SENTIMENT_DIVERGENCE', label: 'Sentiment' },
  { value: 'VOLUME_SURGE', label: 'Volume' },
  { value: 'SOCIAL_SPIKE', label: 'Social' },
  { value: 'PRICE_MOMENTUM', label: 'Momentum' },
];

const PAGE_SIZE = 12;

export default function SignalsPage() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<SignalStatus | 'ALL'>('ALL');
  const [typeFilter, setTypeFilter] = useState<SignalType | 'ALL'>('ALL');

  const fetchSignals = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const params: Record<string, string | number> = {
        limit: PAGE_SIZE,
        offset,
      };

      if (statusFilter !== 'ALL') {
        params.status = statusFilter;
      }
      if (typeFilter !== 'ALL') {
        params.signal_type = typeFilter;
      }

      const data = await signalsApi.list(params);
      setSignals(data.signals);
      setTotal(data.total);
    } catch (err) {
      setError('Failed to load signals');
      console.error(err);
    } finally {
      setLoading(false);
    }
  }, [offset, statusFilter, typeFilter]);

  useEffect(() => {
    fetchSignals();
  }, [fetchSignals]);

  // Reset offset when filters change
  useEffect(() => {
    setOffset(0);
  }, [statusFilter, typeFilter]);

  const hasMore = offset + PAGE_SIZE < total;
  const hasPrev = offset > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white">Signals</h1>
        <p className="text-zinc-400 mt-1">
          Browse all trading signals with their performance data.
        </p>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-4">
        {/* Status Filter */}
        <div className="flex flex-wrap gap-2">
          {SIGNAL_STATUSES.map((status) => (
            <Button
              key={status.value}
              variant="outline"
              size="sm"
              onClick={() => setStatusFilter(status.value)}
              className={cn(
                "border-zinc-700",
                statusFilter === status.value
                  ? "bg-zinc-700 text-white border-zinc-600"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              )}
            >
              {status.label}
            </Button>
          ))}
        </div>

        {/* Type Filter */}
        <div className="flex flex-wrap gap-2">
          {SIGNAL_TYPES.map((type) => (
            <Button
              key={type.value}
              variant="outline"
              size="sm"
              onClick={() => setTypeFilter(type.value)}
              className={cn(
                "border-zinc-700",
                typeFilter === type.value
                  ? "bg-zinc-700 text-white border-zinc-600"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-800"
              )}
            >
              {type.label}
            </Button>
          ))}
        </div>
      </div>

      {/* Results Summary */}
      <div className="text-sm text-zinc-500">
        {!loading && (
          <>
            Showing {signals.length > 0 ? offset + 1 : 0}-{Math.min(offset + PAGE_SIZE, total)} of {total} signals
          </>
        )}
      </div>

      {/* Signal Grid */}
      {loading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="bg-zinc-900 border-zinc-800">
              <CardContent className="pt-6">
                <div className="h-6 bg-zinc-800 rounded w-20 mb-4 animate-pulse" />
                <div className="h-4 bg-zinc-800 rounded w-full mb-2 animate-pulse" />
                <div className="h-4 bg-zinc-800 rounded w-3/4 mb-4 animate-pulse" />
                <div className="grid grid-cols-2 gap-4">
                  <div className="h-12 bg-zinc-800 rounded animate-pulse" />
                  <div className="h-12 bg-zinc-800 rounded animate-pulse" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : error ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="py-8 text-center">
            <p className="text-red-500">{error}</p>
            <Button
              onClick={fetchSignals}
              variant="outline"
              className="mt-4 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Try Again
            </Button>
          </CardContent>
        </Card>
      ) : signals.length === 0 ? (
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="py-8 text-center">
            <p className="text-zinc-400">No signals found with the current filters.</p>
            <Button
              onClick={() => {
                setStatusFilter('ALL');
                setTypeFilter('ALL');
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
          {signals.map((signal) => (
            <SignalCard key={signal.id} signal={signal} showDetails />
          ))}
        </div>
      )}

      {/* Pagination */}
      {!loading && signals.length > 0 && (hasPrev || hasMore) && (
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
    </div>
  );
}
