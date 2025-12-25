'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { subscriptionsApi } from '@/lib/api';

export function EmailCapture() {
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'loading' | 'success' | 'error'>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email) return;

    setStatus('loading');
    setErrorMessage('');

    try {
      const response = await subscriptionsApi.subscribe(email);
      if (response.success) {
        setStatus('success');
        setEmail('');
      } else {
        setStatus('error');
        setErrorMessage(response.message || 'Subscription failed');
      }
    } catch (error) {
      setStatus('error');
      setErrorMessage('Failed to subscribe. Please try again.');
      console.error('Subscription error:', error);
    }
  };

  if (status === 'success') {
    return (
      <div className="bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-6 text-center">
        <div className="text-emerald-500 text-2xl mb-2">✓</div>
        <h3 className="text-lg font-semibold text-white mb-1">You&apos;re on the list!</h3>
        <p className="text-zinc-400 text-sm">
          We&apos;ll notify you when we launch and send you our best signals.
        </p>
      </div>
    );
  }

  return (
    <div id="alerts" className="bg-zinc-900 border border-zinc-800 rounded-lg p-6">
      <h3 className="text-lg font-semibold text-white mb-2">
        Get Trade Signals in Your Inbox
      </h3>
      <p className="text-zinc-400 text-sm mb-4">
        Be the first to know when we spot high-confidence opportunities.
        No spam, just signals.
      </p>
      <form onSubmit={handleSubmit} className="flex gap-2">
        <Input
          type="email"
          placeholder="your@email.com"
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (status === 'error') setStatus('idle');
          }}
          className="flex-1 bg-zinc-800 border-zinc-700 text-white placeholder:text-zinc-500"
          required
        />
        <Button
          type="submit"
          disabled={status === 'loading'}
          className="bg-emerald-600 hover:bg-emerald-500 text-white"
        >
          {status === 'loading' ? 'Joining...' : 'Get Alerts'}
        </Button>
      </form>
      {status === 'error' && errorMessage && (
        <p className="text-red-500 text-sm mt-2">{errorMessage}</p>
      )}
      <p className="text-zinc-500 text-xs mt-3">
        Free alerts. Unsubscribe anytime.
      </p>
    </div>
  );
}
