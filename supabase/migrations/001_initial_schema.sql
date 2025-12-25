-- PolyEdge Initial Schema
-- Run this in Supabase SQL Editor or via migrations

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- MARKETS TABLE
-- Cached market data from Polymarket
-- ============================================
CREATE TABLE IF NOT EXISTS markets (
    id TEXT PRIMARY KEY,
    condition_id TEXT UNIQUE NOT NULL,
    question TEXT NOT NULL,
    slug TEXT,
    description TEXT,
    category TEXT,
    tags TEXT[], -- Array of tag strings

    -- Market state
    active BOOLEAN DEFAULT TRUE,
    closed BOOLEAN DEFAULT FALSE,
    archived BOOLEAN DEFAULT FALSE,
    accepting_orders BOOLEAN DEFAULT TRUE,

    -- Timestamps
    start_date TIMESTAMPTZ,
    end_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Trading data
    volume DECIMAL DEFAULT 0,
    volume_24h DECIMAL DEFAULT 0,
    liquidity DECIMAL DEFAULT 0,

    -- Outcomes
    outcomes TEXT[], -- Array of outcome strings
    outcome_prices TEXT, -- JSON string of prices
    clob_token_ids TEXT, -- JSON string of token IDs

    -- Computed fields
    tier TEXT CHECK (tier IN ('THIN', 'LOW', 'MEDIUM', 'HIGH')),
    current_price DECIMAL
);

CREATE INDEX idx_markets_condition_id ON markets(condition_id);
CREATE INDEX idx_markets_slug ON markets(slug);
CREATE INDEX idx_markets_tier ON markets(tier);
CREATE INDEX idx_markets_active ON markets(active);
CREATE INDEX idx_markets_volume ON markets(volume DESC);

-- ============================================
-- MARKET PRICE HISTORY
-- Point-in-time price snapshots for charts
-- ============================================
CREATE TABLE IF NOT EXISTS market_prices (
    id BIGSERIAL PRIMARY KEY,
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,
    price DECIMAL NOT NULL,
    volume_24h DECIMAL,
    liquidity DECIMAL,
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_market_prices_lookup ON market_prices(market_id, recorded_at DESC);

-- ============================================
-- NEWS SENTIMENT
-- Aggregated news sentiment per market
-- ============================================
CREATE TABLE IF NOT EXISTS news_sentiment (
    id BIGSERIAL PRIMARY KEY,
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,

    -- Sentiment scores
    sentiment_score DECIMAL NOT NULL CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    confidence DECIMAL CHECK (confidence >= 0 AND confidence <= 1),

    -- Article stats
    article_count INTEGER DEFAULT 0,
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    neutral_count INTEGER DEFAULT 0,

    -- Headlines
    top_headlines TEXT[], -- Array of headline strings
    sources TEXT[], -- Array of source names

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_news_sentiment_market ON news_sentiment(market_id, recorded_at DESC);

-- ============================================
-- SOCIAL MENTIONS
-- Twitter/X mention tracking per market
-- ============================================
CREATE TABLE IF NOT EXISTS social_mentions (
    id BIGSERIAL PRIMARY KEY,
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,
    platform TEXT DEFAULT 'twitter',

    -- Mention counts
    mention_count_1h INTEGER DEFAULT 0,
    mention_count_24h INTEGER DEFAULT 0,
    mention_count_7d INTEGER DEFAULT 0,

    -- Engagement
    total_likes INTEGER DEFAULT 0,
    total_retweets INTEGER DEFAULT 0,
    total_replies INTEGER DEFAULT 0,

    -- Velocity
    mention_velocity DECIMAL DEFAULT 0,
    velocity_change_pct DECIMAL DEFAULT 0,

    -- Top tweets (array of tweet IDs)
    top_tweet_ids TEXT[],

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_social_mentions_market ON social_mentions(market_id, recorded_at DESC);

-- ============================================
-- SOCIAL SENTIMENT
-- Sentiment analysis from social media
-- ============================================
CREATE TABLE IF NOT EXISTS social_sentiment (
    id BIGSERIAL PRIMARY KEY,
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,
    platform TEXT DEFAULT 'twitter',

    -- Sentiment
    sentiment_score DECIMAL CHECK (sentiment_score >= -1 AND sentiment_score <= 1),
    confidence DECIMAL CHECK (confidence >= 0 AND confidence <= 1),

    -- Breakdown percentages
    positive_pct DECIMAL DEFAULT 0,
    negative_pct DECIMAL DEFAULT 0,
    neutral_pct DECIMAL DEFAULT 0,

    posts_analyzed INTEGER DEFAULT 0,

    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_social_sentiment_market ON social_sentiment(market_id, recorded_at DESC);

-- ============================================
-- SIGNALS - THE CORE TABLE
-- All trade signals with full context
-- ============================================
CREATE TABLE IF NOT EXISTS signals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    -- Market context at signal time
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,
    market_question TEXT NOT NULL,
    market_slug TEXT,
    market_end_date TIMESTAMPTZ,

    -- Signal details
    signal_type TEXT NOT NULL CHECK (signal_type IN (
        'SENTIMENT_DIVERGENCE',
        'VOLUME_SURGE',
        'SOCIAL_SPIKE',
        'PRICE_MOMENTUM',
        'ARBITRAGE'
    )),
    direction TEXT NOT NULL CHECK (direction IN ('BUY', 'SELL')),
    confidence DECIMAL NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasoning TEXT NOT NULL,

    -- Market state at signal time
    entry_price DECIMAL NOT NULL CHECK (entry_price >= 0 AND entry_price <= 1),
    entry_volume_24h DECIMAL DEFAULT 0,
    entry_volume_total DECIMAL DEFAULT 0,
    entry_liquidity DECIMAL DEFAULT 0,
    market_tier TEXT CHECK (market_tier IN ('THIN', 'LOW', 'MEDIUM', 'HIGH')),

    -- External context at signal time
    news_sentiment_score DECIMAL CHECK (news_sentiment_score >= -1 AND news_sentiment_score <= 1),
    social_mention_count_24h INTEGER,
    social_sentiment_score DECIMAL CHECK (social_sentiment_score >= -1 AND social_sentiment_score <= 1),

    -- Performance tracking (updated by cron job)
    price_1h DECIMAL,
    price_24h DECIMAL,
    price_7d DECIMAL,
    price_at_resolution DECIMAL,

    -- Calculated gains
    gain_1h_pct DECIMAL,
    gain_24h_pct DECIMAL,
    gain_7d_pct DECIMAL,
    gain_final_pct DECIMAL,

    -- Resolution
    status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'RESOLVED_WIN', 'RESOLVED_LOSS', 'EXPIRED')),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_created ON signals(created_at DESC);
CREATE INDEX idx_signals_market ON signals(market_id);
CREATE INDEX idx_signals_type ON signals(signal_type);

-- ============================================
-- USER PROFILES
-- Extended profile data (Supabase Auth handles auth)
-- ============================================
CREATE TABLE IF NOT EXISTS profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    email TEXT,
    display_name TEXT,

    -- Alert preferences (JSONB for flexibility)
    alert_preferences JSONB DEFAULT '{
        "email_enabled": true,
        "webhook_enabled": false,
        "webhook_url": null,
        "min_confidence": 0.5,
        "signal_types": ["SENTIMENT_DIVERGENCE", "VOLUME_SURGE", "SOCIAL_SPIKE", "PRICE_MOMENTUM"]
    }'::jsonb,

    -- Tracking
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================
-- USER SIGNAL FOLLOWS
-- Track which signals a user followed
-- ============================================
CREATE TABLE IF NOT EXISTS user_signal_follows (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES signals(id) ON DELETE CASCADE,

    -- User's actual trade (optional, for personal tracking)
    followed_at TIMESTAMPTZ DEFAULT NOW(),
    entry_price_actual DECIMAL, -- User's actual entry if different
    exit_price DECIMAL, -- User's exit price
    position_size DECIMAL, -- How much they invested
    notes TEXT,

    UNIQUE(user_id, signal_id)
);

CREATE INDEX idx_user_follows_user ON user_signal_follows(user_id);
CREATE INDEX idx_user_follows_signal ON user_signal_follows(signal_id);

-- ============================================
-- USER WATCHLIST
-- Markets a user is watching
-- ============================================
CREATE TABLE IF NOT EXISTS user_watchlist (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    market_id TEXT REFERENCES markets(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    notes TEXT,

    UNIQUE(user_id, market_id)
);

CREATE INDEX idx_watchlist_user ON user_watchlist(user_id);

-- ============================================
-- ALERT LOG
-- Track all alerts sent
-- ============================================
CREATE TABLE IF NOT EXISTS alert_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES profiles(id) ON DELETE CASCADE,
    signal_id UUID REFERENCES signals(id) ON DELETE CASCADE,

    channel TEXT NOT NULL CHECK (channel IN ('email', 'webhook', 'push')),
    status TEXT DEFAULT 'sent' CHECK (status IN ('sent', 'failed', 'bounced')),

    sent_at TIMESTAMPTZ DEFAULT NOW(),
    error_message TEXT
);

CREATE INDEX idx_alert_log_user ON alert_log(user_id, sent_at DESC);

-- ============================================
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ============================================

-- Enable RLS on user-specific tables
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_signal_follows ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_watchlist ENABLE ROW LEVEL SECURITY;
ALTER TABLE alert_log ENABLE ROW LEVEL SECURITY;

-- Profiles: Users can only see/edit their own profile
CREATE POLICY "Users can view own profile" ON profiles
    FOR SELECT USING (auth.uid() = id);

CREATE POLICY "Users can update own profile" ON profiles
    FOR UPDATE USING (auth.uid() = id);

-- Signal follows: Users can only see/manage their own follows
CREATE POLICY "Users can view own follows" ON user_signal_follows
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own follows" ON user_signal_follows
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own follows" ON user_signal_follows
    FOR DELETE USING (auth.uid() = user_id);

-- Watchlist: Users can only see/manage their own watchlist
CREATE POLICY "Users can view own watchlist" ON user_watchlist
    FOR SELECT USING (auth.uid() = user_id);

CREATE POLICY "Users can insert to own watchlist" ON user_watchlist
    FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete from own watchlist" ON user_watchlist
    FOR DELETE USING (auth.uid() = user_id);

-- Alert log: Users can only see their own alerts
CREATE POLICY "Users can view own alerts" ON alert_log
    FOR SELECT USING (auth.uid() = user_id);

-- Public tables (everyone can read)
-- Markets, signals, sentiment data are public read
ALTER TABLE markets ENABLE ROW LEVEL SECURITY;
ALTER TABLE signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE news_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_mentions ENABLE ROW LEVEL SECURITY;
ALTER TABLE social_sentiment ENABLE ROW LEVEL SECURITY;
ALTER TABLE market_prices ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Markets are public read" ON markets FOR SELECT USING (true);
CREATE POLICY "Signals are public read" ON signals FOR SELECT USING (true);
CREATE POLICY "News sentiment is public read" ON news_sentiment FOR SELECT USING (true);
CREATE POLICY "Social mentions are public read" ON social_mentions FOR SELECT USING (true);
CREATE POLICY "Social sentiment is public read" ON social_sentiment FOR SELECT USING (true);
CREATE POLICY "Market prices are public read" ON market_prices FOR SELECT USING (true);

-- ============================================
-- FUNCTIONS & TRIGGERS
-- ============================================

-- Auto-update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_markets_updated_at
    BEFORE UPDATE ON markets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_profiles_updated_at
    BEFORE UPDATE ON profiles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Auto-create profile when user signs up
CREATE OR REPLACE FUNCTION handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO profiles (id, email)
    VALUES (NEW.id, NEW.email);
    RETURN NEW;
END;
$$ language 'plpgsql' SECURITY DEFINER;

CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION handle_new_user();

-- ============================================
-- VIEWS FOR COMMON QUERIES
-- ============================================

-- Signal stats view for track record
CREATE OR REPLACE VIEW signal_stats AS
SELECT
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE status = 'ACTIVE') as active_signals,
    COUNT(*) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')) as resolved_signals,
    COUNT(*) FILTER (WHERE status = 'RESOLVED_WIN') as wins,
    COUNT(*) FILTER (WHERE status = 'RESOLVED_LOSS') as losses,
    CASE
        WHEN COUNT(*) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE status = 'RESOLVED_WIN')::DECIMAL /
            COUNT(*) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')) * 100,
            1
        )
        ELSE 0
    END as win_rate_pct,
    ROUND(AVG(gain_final_pct) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')), 2) as avg_gain_pct,
    ROUND(MAX(gain_final_pct) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')), 2) as best_gain_pct,
    ROUND(MIN(gain_final_pct) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')), 2) as worst_gain_pct
FROM signals;

-- Signal stats by type
CREATE OR REPLACE VIEW signal_stats_by_type AS
SELECT
    signal_type,
    COUNT(*) as total_signals,
    COUNT(*) FILTER (WHERE status = 'RESOLVED_WIN') as wins,
    COUNT(*) FILTER (WHERE status = 'RESOLVED_LOSS') as losses,
    CASE
        WHEN COUNT(*) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')) > 0
        THEN ROUND(
            COUNT(*) FILTER (WHERE status = 'RESOLVED_WIN')::DECIMAL /
            COUNT(*) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')) * 100,
            1
        )
        ELSE 0
    END as win_rate_pct,
    ROUND(AVG(gain_final_pct) FILTER (WHERE status IN ('RESOLVED_WIN', 'RESOLVED_LOSS')), 2) as avg_gain_pct
FROM signals
GROUP BY signal_type;

-- Active signals with market data
CREATE OR REPLACE VIEW active_signals_view AS
SELECT
    s.*,
    m.question as current_question,
    m.current_price as current_market_price,
    m.volume_24h as current_volume_24h,
    CASE
        WHEN s.direction = 'BUY' THEN ROUND((m.current_price - s.entry_price) / s.entry_price * 100, 2)
        ELSE ROUND((s.entry_price - m.current_price) / s.entry_price * 100, 2)
    END as current_gain_pct
FROM signals s
JOIN markets m ON s.market_id = m.id
WHERE s.status = 'ACTIVE';
