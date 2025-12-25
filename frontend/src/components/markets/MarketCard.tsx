import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { Market } from '@/types';
import { cn } from '@/lib/utils';

interface MarketCardProps {
  market: Market;
}

const tierColors: Record<string, string> = {
  THIN: 'border-zinc-600 text-zinc-400',
  LOW: 'border-yellow-500/50 text-yellow-500',
  MEDIUM: 'border-blue-500/50 text-blue-500',
  HIGH: 'border-emerald-500/50 text-emerald-500',
};

export function MarketCard({ market }: MarketCardProps) {
  const formatVolume = (volume: number) => {
    if (volume >= 1000000) return `$${(volume / 1000000).toFixed(1)}M`;
    if (volume >= 1000) return `$${(volume / 1000).toFixed(0)}K`;
    return `$${volume.toFixed(0)}`;
  };

  const formatPrice = (price: number) => {
    return `${(price * 100).toFixed(0)}%`;
  };

  return (
    <Card className="bg-zinc-900 border-zinc-800 hover:border-zinc-700 transition-colors">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <Badge
            variant="outline"
            className={cn("font-medium", tierColors[market.tier] || tierColors.THIN)}
          >
            {market.tier}
          </Badge>
          {market.has_active_signal && (
            <Badge className="bg-emerald-500/20 text-emerald-500 border-emerald-500/50">
              Active Signal
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <h3 className="text-white font-medium line-clamp-2 min-h-[48px]">
          {market.question}
        </h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-zinc-500">Current Price</div>
            <div className="text-white font-medium text-lg">
              {market.current_price !== null ? formatPrice(market.current_price) : '—'}
            </div>
          </div>
          <div>
            <div className="text-zinc-500">Volume</div>
            <div className="text-white font-medium text-lg">
              {formatVolume(market.volume_24h)}
            </div>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-zinc-800">
          <span className="text-zinc-500 text-xs">
            {market.category || 'Uncategorized'}
          </span>
          <Button
            variant="ghost"
            size="sm"
            asChild
            className="text-zinc-400 hover:text-white"
          >
            <a
              href={`https://polymarket.com/event/${market.slug || market.condition_id}`}
              target="_blank"
              rel="noopener noreferrer"
            >
              View on Polymarket
            </a>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}

export function MarketCardSkeleton() {
  return (
    <Card className="bg-zinc-900 border-zinc-800">
      <CardHeader className="pb-2">
        <div className="h-5 bg-zinc-800 rounded w-16 animate-pulse" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="h-12 bg-zinc-800 rounded animate-pulse" />
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="h-3 bg-zinc-800 rounded w-12 mb-2 animate-pulse" />
            <div className="h-6 bg-zinc-800 rounded w-16 animate-pulse" />
          </div>
          <div>
            <div className="h-3 bg-zinc-800 rounded w-12 mb-2 animate-pulse" />
            <div className="h-6 bg-zinc-800 rounded w-16 animate-pulse" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
