'use client';

import { useEffect, useState } from 'react';
import { StatsHero, StatsHeroSkeleton } from '@/components/track-record/StatsHero';
import { SignalHistory } from '@/components/track-record/SignalHistory';
import { trackRecordApi } from '@/lib/api';
import type { TrackRecordResponse } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

export default function TrackRecordPage() {
  const [data, setData] = useState<TrackRecordResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const trackRecord = await trackRecordApi.summary();
        setData(trackRecord);
      } catch (err) {
        setError('Failed to load track record');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  const handleExport = async () => {
    try {
      setExporting(true);
      const blob = await trackRecordApi.export();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `polyedge-track-record-${new Date().toISOString().split('T')[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Export failed:', err);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white">Track Record</h1>
          <p className="text-zinc-400 mt-1">
            Full transparency on every signal we&apos;ve generated.
          </p>
        </div>
        <Button
          onClick={handleExport}
          disabled={exporting}
          variant="outline"
          className="border-zinc-700 text-zinc-300 hover:bg-zinc-800"
        >
          {exporting ? 'Exporting...' : 'Export CSV'}
        </Button>
      </div>

      {/* Stats Summary */}
      <section>
        {loading ? (
          <StatsHeroSkeleton />
        ) : error ? (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="py-8 text-center">
              <p className="text-red-500">{error}</p>
            </CardContent>
          </Card>
        ) : data ? (
          <StatsHero summary={data.summary} />
        ) : null}
      </section>

      {/* Performance by Signal Type */}
      {data && data.by_signal_type && data.by_signal_type.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold text-white mb-4">Performance by Signal Type</h2>
          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-4">
            {data.by_signal_type.map((stats) => {
              const isPositive = stats.avg_gain_pct > 0;
              const typeLabel = stats.signal_type.split('_').map(w =>
                w.charAt(0) + w.slice(1).toLowerCase()
              ).join(' ');

              return (
                <Card key={stats.signal_type} className="bg-zinc-900 border-zinc-800">
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-zinc-400">
                      {typeLabel}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-baseline justify-between">
                      <span className="text-2xl font-bold text-white">
                        {stats.win_rate_pct.toFixed(0)}%
                      </span>
                      <span className="text-sm text-zinc-500">
                        Win Rate
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Avg Gain</span>
                      <span className={cn(
                        "font-medium",
                        isPositive ? "text-emerald-500" : "text-red-500"
                      )}>
                        {isPositive ? '+' : ''}{stats.avg_gain_pct.toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">Signals</span>
                      <span className="text-white">{stats.total_signals}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-zinc-400">W/L</span>
                      <span className="text-zinc-300">
                        {stats.wins}W - {stats.losses}L
                      </span>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {/* Signal History Table */}
      <section>
        <h2 className="text-xl font-semibold text-white mb-4">Signal History</h2>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <SignalHistory limit={15} showPagination={true} />
          </CardContent>
        </Card>
      </section>

      {/* Methodology */}
      <section>
        <Card className="bg-zinc-900 border-zinc-800">
          <CardHeader>
            <CardTitle className="text-lg text-white">How We Calculate Performance</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-zinc-400 text-sm">
            <p>
              <strong className="text-white">Entry Price:</strong> The market price at the time the signal was generated.
            </p>
            <p>
              <strong className="text-white">Exit Price:</strong> The market price when the position is resolved (market settles or signal is closed).
            </p>
            <p>
              <strong className="text-white">Gain Calculation:</strong> For BUY signals, gain = (exit - entry) / entry * 100. For SELL signals, gain = (entry - exit) / entry * 100.
            </p>
            <p>
              <strong className="text-white">Win/Loss:</strong> A signal is counted as a win if the final gain is positive.
            </p>
            <p>
              <strong className="text-white">Theoretical Return:</strong> Assumes $1,000 invested per signal, compounded.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
