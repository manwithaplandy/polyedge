import type {
  SignalListResponse,
  SignalStats,
  Signal,
  MarketListResponse,
  Market,
  TrackRecordResponse,
  SignalHistoryResponse,
  HealthResponse,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Signal API
export const signalsApi = {
  list: (params?: {
    status?: string;
    signal_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<SignalListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.signal_type) searchParams.set('signal_type', params.signal_type);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return fetchApi<SignalListResponse>(`/api/signals${query ? `?${query}` : ''}`);
  },

  active: (): Promise<SignalListResponse> => {
    return fetchApi<SignalListResponse>('/api/signals/active');
  },

  stats: (): Promise<SignalStats> => {
    return fetchApi<SignalStats>('/api/signals/stats');
  },

  get: (id: string): Promise<Signal> => {
    return fetchApi<Signal>(`/api/signals/${id}`);
  },
};

// Markets API
export const marketsApi = {
  list: (params?: {
    tier?: string;
    active?: boolean;
    has_active_signal?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<MarketListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.tier) searchParams.set('tier', params.tier);
    if (params?.active !== undefined) searchParams.set('active', params.active.toString());
    if (params?.has_active_signal !== undefined) searchParams.set('has_active_signal', params.has_active_signal.toString());
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return fetchApi<MarketListResponse>(`/api/markets${query ? `?${query}` : ''}`);
  },

  get: (id: string): Promise<Market> => {
    return fetchApi<Market>(`/api/markets/${id}`);
  },

  byTier: (tier: string, params?: { limit?: number; offset?: number }): Promise<MarketListResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return fetchApi<MarketListResponse>(`/api/markets/tier/${tier}${query ? `?${query}` : ''}`);
  },
};

// Track Record API
export const trackRecordApi = {
  summary: (): Promise<TrackRecordResponse> => {
    return fetchApi<TrackRecordResponse>('/api/track-record');
  },

  history: (params?: {
    status?: string;
    signal_type?: string;
    limit?: number;
    offset?: number;
  }): Promise<SignalHistoryResponse> => {
    const searchParams = new URLSearchParams();
    if (params?.status) searchParams.set('status', params.status);
    if (params?.signal_type) searchParams.set('signal_type', params.signal_type);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    if (params?.offset) searchParams.set('offset', params.offset.toString());

    const query = searchParams.toString();
    return fetchApi<SignalHistoryResponse>(`/api/track-record/history${query ? `?${query}` : ''}`);
  },

  exportUrl: (): string => {
    return `${API_BASE}/api/track-record/export`;
  },

  export: async (): Promise<Blob> => {
    const response = await fetch(`${API_BASE}/api/track-record/export`);
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status}`);
    }
    return response.blob();
  },
};

// Subscriptions API
export interface SubscriptionResponse {
  success: boolean;
  message: string;
  email?: string;
}

export const subscriptionsApi = {
  subscribe: (email: string, source: string = 'website'): Promise<SubscriptionResponse> => {
    return fetchApi<SubscriptionResponse>('/api/subscriptions', {
      method: 'POST',
      body: JSON.stringify({ email, source }),
    });
  },
};

// Health API
export const healthApi = {
  check: (): Promise<HealthResponse> => {
    return fetchApi<HealthResponse>('/health');
  },

  detailed: (): Promise<HealthResponse> => {
    return fetchApi<HealthResponse>('/health/detailed');
  },
};

// Combined API export
export const api = {
  signals: signalsApi,
  markets: marketsApi,
  trackRecord: trackRecordApi,
  subscriptions: subscriptionsApi,
  health: healthApi,
};
