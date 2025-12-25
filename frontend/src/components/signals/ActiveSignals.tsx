'use client';

import { useEffect, useState } from 'react';
import { SignalCard } from './SignalCard';
import { signalsApi } from '@/lib/api';
import type { Signal } from '@/types';
import { Card, CardContent } from '@/components/ui/card';

export function ActiveSignals() {
  const [signals, setSignals] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchSignals() {
      try {
        const data = await signalsApi.active();
        setSignals(data.signals);
      } catch (err) {
        setError('Failed to load signals');
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchSignals();
  }, []);

  if (loading) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {[1, 2, 3].map((i) => (
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
    );
  }

  if (error) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-8 text-center">
          <p className="text-red-500">{error}</p>
          <p className="text-zinc-500 text-sm mt-2">
            Make sure the backend is running at localhost:8000
          </p>
        </CardContent>
      </Card>
    );
  }

  if (signals.length === 0) {
    return (
      <Card className="bg-zinc-900 border-zinc-800">
        <CardContent className="py-8 text-center">
          <div className="text-4xl mb-4">📊</div>
          <h3 className="text-lg font-medium text-white mb-2">No Active Signals</h3>
          <p className="text-zinc-500">
            We&apos;re constantly scanning for opportunities. Check back soon!
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {signals.map((signal) => (
        <SignalCard key={signal.id} signal={signal} />
      ))}
    </div>
  );
}
