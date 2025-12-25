'use client';

import { useEffect, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { trackRecordApi } from '@/lib/api';
import type { SignalHistoryItem } from '@/types';
import { cn } from '@/lib/utils';

interface SignalHistoryProps {
  limit?: number;
  showPagination?: boolean;
}

export function SignalHistory({ limit = 10, showPagination = true }: SignalHistoryProps) {
  const [signals, setSignals] = useState<SignalHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      try {
        setLoading(true);
        const data = await trackRecordApi.history({ limit, offset });
        setSignals(data.signals);
        setTotal(data.total);
      } catch (err) {
        setError('Failed to load signal history');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchHistory();
  }, [limit, offset]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const hasMore = offset + limit < total;
  const hasPrev = offset > 0;

  if (loading && signals.length === 0) {
    return <SignalHistorySkeleton />;
  }

  if (error) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-8 text-center">
          <p className="text-red-500">{error}</p>
        </CardContent>
      </Card>
    );
  }

  if (signals.length === 0) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-8 text-center">
          <p className="text-zinc-500">No signal history yet.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-sm text-zinc-500">
              <th className="pb-3 pr-4">Date</th>
              <th className="pb-3 pr-4">Market</th>
              <th className="pb-3 pr-4">Direction</th>
              <th className="pb-3 pr-4">Type</th>
              <th className="pb-3 pr-4 text-right">Entry</th>
              <th className="pb-3 pr-4 text-right">Exit</th>
              <th className="pb-3 text-right">Result</th>
            </tr>
          </thead>
          <tbody>
            {signals.map((signal) => {
              const isWin = signal.status === 'RESOLVED_WIN';
              const hasGain = signal.gain_pct !== null;

              return (
                <tr
                  key={signal.id}
                  className="border-b border-zinc-800/50 text-sm hover:bg-zinc-800/30"
                >
                  <td className="py-3 pr-4 text-zinc-400">
                    {formatDate(signal.date)}
                  </td>
                  <td className="py-3 pr-4 max-w-xs">
                    <span className="text-white line-clamp-1">
                      {signal.market_question}
                    </span>
                  </td>
                  <td className="py-3 pr-4">
                    <Badge
                      variant="outline"
                      className={cn(
                        "font-medium",
                        signal.direction === 'BUY'
                          ? "border-emerald-500/50 text-emerald-500"
                          : "border-red-500/50 text-red-500"
                      )}
                    >
                      {signal.direction}
                    </Badge>
                  </td>
                  <td className="py-3 pr-4 text-zinc-400">
                    {signal.signal_type.split('_').map(w =>
                      w.charAt(0) + w.slice(1).toLowerCase()
                    ).join(' ')}
                  </td>
                  <td className="py-3 pr-4 text-right text-white">
                    ${signal.entry_price.toFixed(2)}
                  </td>
                  <td className="py-3 pr-4 text-right text-white">
                    {signal.exit_price !== null
                      ? `$${signal.exit_price.toFixed(2)}`
                      : '—'
                    }
                  </td>
                  <td className="py-3 text-right">
                    {hasGain ? (
                      <span className={cn(
                        "font-medium",
                        isWin ? "text-emerald-500" : "text-red-500"
                      )}>
                        {signal.gain_pct! > 0 ? '+' : ''}
                        {signal.gain_pct!.toFixed(1)}%
                      </span>
                    ) : (
                      <Badge variant="outline" className="border-zinc-700 text-zinc-400">
                        {signal.status === 'ACTIVE' ? 'Active' : 'Pending'}
                      </Badge>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {showPagination && (hasPrev || hasMore) && (
        <div className="flex items-center justify-between pt-4">
          <div className="text-sm text-zinc-500">
            Showing {offset + 1}-{Math.min(offset + limit, total)} of {total}
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOffset(Math.max(0, offset - limit))}
              disabled={!hasPrev || loading}
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setOffset(offset + limit)}
              disabled={!hasMore || loading}
              className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}

function SignalHistorySkeleton() {
  return (
    <div className="space-y-3">
      {[1, 2, 3, 4, 5].map((i) => (
        <div key={i} className="flex gap-4 py-3 border-b border-zinc-800/50">
          <div className="h-4 bg-zinc-800 rounded w-20 animate-pulse" />
          <div className="h-4 bg-zinc-800 rounded flex-1 animate-pulse" />
          <div className="h-4 bg-zinc-800 rounded w-16 animate-pulse" />
          <div className="h-4 bg-zinc-800 rounded w-16 animate-pulse" />
        </div>
      ))}
    </div>
  );
}
