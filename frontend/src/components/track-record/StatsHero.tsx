import { Card, CardContent } from '@/components/ui/card';
import type { TrackRecordSummary } from '@/types';
import { cn } from '@/lib/utils';

interface StatsHeroProps {
  summary: TrackRecordSummary;
  compact?: boolean;
}

export function StatsHero({ summary, compact = false }: StatsHeroProps) {
  const stats = [
    {
      label: 'Win Rate',
      value: `${summary.win_rate_pct.toFixed(1)}%`,
      description: `${summary.wins}W - ${summary.losses}L`,
      positive: summary.win_rate_pct > 50,
    },
    {
      label: 'Avg Gain',
      value: `${summary.avg_gain_pct > 0 ? '+' : ''}${summary.avg_gain_pct.toFixed(1)}%`,
      description: 'Per signal',
      positive: summary.avg_gain_pct > 0,
    },
    {
      label: 'Total Signals',
      value: summary.total_signals.toString(),
      description: `${summary.active_signals} active`,
      positive: true,
    },
    {
      label: 'If $1K/Signal',
      value: `$${Math.round(summary.theoretical_return_1k).toLocaleString()}`,
      description: 'Theoretical profit',
      positive: summary.theoretical_return_1k > 0,
    },
  ];

  if (compact) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {stats.map((stat) => (
          <div key={stat.label} className="text-center">
            <div className={cn(
              "text-2xl font-bold",
              stat.positive ? "text-emerald-500" : "text-red-500"
            )}>
              {stat.value}
            </div>
            <div className="text-zinc-400 text-sm">{stat.label}</div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {stats.map((stat) => (
        <Card key={stat.label} className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <div className="text-zinc-400 text-sm mb-1">{stat.label}</div>
            <div className={cn(
              "text-3xl font-bold mb-1",
              stat.positive ? "text-emerald-500" : "text-red-500"
            )}>
              {stat.value}
            </div>
            <div className="text-zinc-500 text-sm">{stat.description}</div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// Loading skeleton
export function StatsHeroSkeleton() {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i} className="bg-zinc-900 border-zinc-800">
          <CardContent className="pt-6">
            <div className="h-4 bg-zinc-800 rounded w-20 mb-2 animate-pulse" />
            <div className="h-8 bg-zinc-800 rounded w-24 mb-2 animate-pulse" />
            <div className="h-3 bg-zinc-800 rounded w-16 animate-pulse" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
