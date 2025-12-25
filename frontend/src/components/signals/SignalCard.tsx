import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import type { Signal } from '@/types';
import { cn } from '@/lib/utils';

interface SignalCardProps {
  signal: Signal;
  showDetails?: boolean;
}

export function SignalCard({ signal, showDetails = false }: SignalCardProps) {
  const isBuy = signal.direction === 'BUY';
  const hasGain = signal.current_gain_pct !== null;
  const isPositive = hasGain && signal.current_gain_pct! > 0;

  const formatSignalType = (type: string) => {
    return type.split('_').map(word =>
      word.charAt(0) + word.slice(1).toLowerCase()
    ).join(' ');
  };

  return (
    <Card className={cn(
      "bg-zinc-900 border-zinc-800 overflow-hidden",
      "border-l-4",
      isBuy ? "border-l-emerald-500" : "border-l-red-500"
    )}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={cn(
                "font-semibold",
                isBuy
                  ? "border-emerald-500/50 bg-emerald-500/10 text-emerald-500"
                  : "border-red-500/50 bg-red-500/10 text-red-500"
              )}
            >
              {signal.direction}
            </Badge>
            <Badge variant="outline" className="border-zinc-700 text-zinc-400">
              {formatSignalType(signal.signal_type)}
            </Badge>
          </div>
          <div className="text-right">
            <div className="text-sm text-zinc-500">Confidence</div>
            <div className="text-lg font-bold text-white">
              {Math.round(signal.confidence * 100)}%
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <h3 className="text-white font-medium mb-3 line-clamp-2">
          {signal.market_question}
        </h3>

        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <div className="text-zinc-500">Entry Price</div>
            <div className="text-white font-medium">
              ${signal.entry_price.toFixed(2)}
            </div>
          </div>
          <div>
            <div className="text-zinc-500">Current Gain</div>
            <div className={cn(
              "font-medium",
              hasGain
                ? isPositive ? "text-emerald-500" : "text-red-500"
                : "text-zinc-400"
            )}>
              {hasGain
                ? `${isPositive ? '+' : ''}${signal.current_gain_pct!.toFixed(1)}%`
                : '—'
              }
            </div>
          </div>
        </div>

        {showDetails && (
          <div className="mt-4 pt-4 border-t border-zinc-800">
            <div className="text-zinc-500 text-sm mb-2">Reasoning</div>
            <p className="text-zinc-300 text-sm">{signal.reasoning}</p>
          </div>
        )}

        <div className="flex items-center justify-between mt-4 pt-3 border-t border-zinc-800">
          <Badge variant="outline" className="border-zinc-700 text-zinc-500 text-xs">
            {signal.market_tier}
          </Badge>
          <span className="text-zinc-500 text-xs">
            {new Date(signal.created_at).toLocaleDateString()}
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
