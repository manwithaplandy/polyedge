'use client';

import { useEffect, useState } from 'react';
import { ActiveSignals } from '@/components/signals/ActiveSignals';
import { StatsHero, StatsHeroSkeleton } from '@/components/track-record/StatsHero';
import { EmailCapture } from '@/components/EmailCapture';
import { SignalCard } from '@/components/signals/SignalCard';
import { trackRecordApi, signalsApi } from '@/lib/api';
import type { TrackRecordSummary, Signal } from '@/types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function Dashboard() {
  const [summary, setSummary] = useState<TrackRecordSummary | null>(null);
  const [recentResolved, setRecentResolved] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [trackRecord, allSignals] = await Promise.all([
          trackRecordApi.summary(),
          signalsApi.list({ limit: 20 }),
        ]);
        setSummary(trackRecord.summary);

        // Get recent resolved signals (wins and losses mixed)
        const resolved = allSignals.signals.filter(
          (s) => s.status === 'RESOLVED_WIN' || s.status === 'RESOLVED_LOSS'
        ).slice(0, 3);
        setRecentResolved(resolved);
      } catch (err) {
        setError('Failed to load dashboard data');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <section className="text-center py-8">
        <h1 className="text-4xl md:text-5xl font-bold text-white mb-4">
          Your Edge in Prediction Markets
        </h1>
        <p className="text-xl text-zinc-400 max-w-2xl mx-auto">
          AI-powered trading signals for Polymarket. Transparent track record.
          Real performance data.
        </p>
      </section>

      {/* Stats Hero */}
      <section>
        <h2 className="text-xl font-semibold text-white mb-4">Our Track Record</h2>
        {loading ? (
          <StatsHeroSkeleton />
        ) : error ? (
          <Card className="bg-zinc-900 border-zinc-800">
            <CardContent className="py-8 text-center">
              <p className="text-red-500">{error}</p>
            </CardContent>
          </Card>
        ) : summary ? (
          <StatsHero summary={summary} />
        ) : null}
        <div className="mt-4 text-center">
          <Link href="/track-record">
            <Button variant="outline" className="border-zinc-700 text-zinc-300 hover:bg-zinc-800">
              View Full Track Record
            </Button>
          </Link>
        </div>
      </section>

      {/* Active Signals */}
      <section>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-white">Active Signals</h2>
          <Link href="/signals">
            <Button variant="ghost" className="text-zinc-400 hover:text-white">
              View All Signals
            </Button>
          </Link>
        </div>
        <ActiveSignals />
      </section>

      {/* Recent Results */}
      {recentResolved.length > 0 && (
        <section>
          <h2 className="text-xl font-semibold text-white mb-4">Recent Results</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {recentResolved.map((signal) => (
              <SignalCard key={signal.id} signal={signal} />
            ))}
          </div>
        </section>
      )}

      {/* Email Capture */}
      <section className="max-w-xl mx-auto">
        <EmailCapture />
      </section>

      {/* How It Works */}
      <section className="py-8">
        <h2 className="text-xl font-semibold text-white mb-6 text-center">How It Works</h2>
        <div className="grid md:grid-cols-3 gap-6">
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-sm font-bold">1</span>
                We Scan Markets
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-400 text-sm">
                Our algorithms monitor Polymarket 24/7, analyzing price movements, volume patterns, and market sentiment.
              </p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-sm font-bold">2</span>
                Cross-Reference News
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-400 text-sm">
                We correlate market data with real-time news and social media sentiment to identify mispriced opportunities.
              </p>
            </CardContent>
          </Card>
          <Card className="bg-zinc-900 border-zinc-800">
            <CardHeader>
              <CardTitle className="text-lg text-white flex items-center gap-2">
                <span className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-500 flex items-center justify-center text-sm font-bold">3</span>
                Generate Signals
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-zinc-400 text-sm">
                High-confidence opportunities become actionable BUY/SELL signals with entry prices and reasoning.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
