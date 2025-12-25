// Signal Types
export type SignalStatus = 'ACTIVE' | 'RESOLVED_WIN' | 'RESOLVED_LOSS' | 'EXPIRED';
export type SignalType = 'SENTIMENT_DIVERGENCE' | 'VOLUME_SURGE' | 'SOCIAL_SPIKE' | 'PRICE_MOMENTUM' | 'ARBITRAGE';
export type SignalDirection = 'BUY' | 'SELL';
export type MarketTier = 'THIN' | 'LOW' | 'MEDIUM' | 'HIGH';

export interface Signal {
  id: string;
  created_at: string;
  market_id: string;
  market_question: string;
  market_slug: string | null;
  signal_type: SignalType;
  direction: SignalDirection;
  confidence: number;
  reasoning: string;
  entry_price: number;
  market_tier: MarketTier;
  status: SignalStatus;
  current_gain_pct: number | null;
  gain_1h_pct: number | null;
  gain_24h_pct: number | null;
  gain_7d_pct: number | null;
  gain_final_pct: number | null;
}

export interface SignalListResponse {
  signals: Signal[];
  total: number;
  offset: number;
  limit: number;
}

export interface SignalStats {
  total_signals: number;
  active_signals: number;
  resolved_signals: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_gain_pct: number;
  best_gain_pct: number;
  worst_gain_pct: number;
  stats_by_type: Record<string, {
    total: number;
    wins: number;
    losses: number;
    win_rate: number;
    avg_gain: number;
  }>;
}

// Market Types
export interface Market {
  id: string;
  condition_id: string;
  question: string;
  slug: string | null;
  description: string | null;
  category: string | null;
  active: boolean;
  closed: boolean;
  volume: number;
  volume_24h: number;
  liquidity: number;
  current_price: number | null;
  tier: MarketTier;
  outcomes: string[];
  end_date: string | null;
  has_active_signal: boolean;
}

export interface MarketListResponse {
  markets: Market[];
  total: number;
  offset: number;
  limit: number;
}

// Track Record Types
export interface TrackRecordSummary {
  total_signals: number;
  active_signals: number;
  resolved_signals: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  avg_gain_pct: number;
  best_gain_pct: number;
  worst_gain_pct: number;
  theoretical_return_1k: number;
}

export interface SignalTypeStats {
  signal_type: string;
  total_signals: number;
  wins: number;
  losses: number;
  win_rate_pct: number;
  avg_gain_pct: number;
  best_gain_pct: number;
}

export interface TrackRecordResponse {
  summary: TrackRecordSummary;
  by_signal_type: SignalTypeStats[];
  last_updated: string;
}

export interface SignalHistoryItem {
  id: string;
  date: string;
  market_question: string;
  signal_type: string;
  direction: SignalDirection;
  confidence: number;
  entry_price: number;
  exit_price: number | null;
  gain_pct: number | null;
  status: SignalStatus;
}

export interface SignalHistoryResponse {
  signals: SignalHistoryItem[];
  total: number;
  offset: number;
  limit: number;
}

// Health Types
export interface HealthResponse {
  status: string;
  service: string;
  environment?: string;
  use_mock_data?: boolean;
  services?: {
    supabase: string;
    newsapi: string;
    twitter: string;
  };
}
