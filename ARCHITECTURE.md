# PolyEdge Architecture Documentation

> **PolyEdge** - "Your edge in prediction markets"
> AI-powered trading signals for Polymarket with transparent track records.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Core Value Proposition](#core-value-proposition)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Backend Architecture](#backend-architecture)
6. [Frontend Architecture](#frontend-architecture)
7. [Database Schema](#database-schema)
8. [Data Flow](#data-flow)
9. [Signal Generation System](#signal-generation-system)
10. [Configuration](#configuration)
11. [Development Setup](#development-setup)

---

## Project Overview

PolyEdge is a platform that monitors Polymarket prediction markets to identify trading opportunities. It correlates market data with external news sources and social media sentiment to generate BUY/SELL signals. The key differentiator is **transparent track record tracking** - every signal is recorded with entry price, volume data, and tracked over time so historical performance can be analyzed.

### Key Features

- **Signal Generation**: Automated detection of trading opportunities using 4 rule types
- **Performance Tracking**: Every signal records entry price and tracks gains at 1h, 24h, 7d, and final resolution
- **Track Record Transparency**: Public display of win rate, average gains, and full signal history
- **CSV Export**: Download complete signal history for independent verification
- **Email Alerts**: Users can subscribe to receive new signals via email

---

## Core Value Proposition

The central insight driving this project: **successful trade suggestions with verifiable track records**.

When a signal is generated, it records:
- Entry price at signal generation time
- Market volume and liquidity
- News sentiment score
- Social media mention counts
- The reasoning behind the signal

As time passes, the system tracks:
- Price at 1 hour, 24 hours, 7 days after signal
- Calculated percentage gains at each interval
- Final outcome when the market resolves

This creates an auditable history that proves (or disproves) the system's effectiveness.

---

## Tech Stack

### Backend
- **Python 3.11+** with **FastAPI** - Async web framework
- **Pydantic** - Data validation and settings management
- **Supabase** - PostgreSQL database with Row Level Security
- **httpx** - Async HTTP client for external APIs
- **boto3** - AWS SDK for SES email sending (planned)

### Frontend
- **Next.js 14** (App Router) - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling
- **shadcn/ui** - Pre-built accessible components
- **React hooks** - State management (no Redux needed for MVP)

### External Data Sources
- **Polymarket Gamma API** - Market data, prices, volumes
- **NewsAPI** - News articles for sentiment analysis
- **Twitter/X API v2** - Social media mentions and sentiment

### Infrastructure
- **Supabase** - Hosted PostgreSQL + Auth + Realtime
- **AWS SES** - Email delivery (cheaper than SendGrid)

---

## Project Structure

```
polyedge/
├── backend/                    # Python FastAPI backend
│   ├── src/
│   │   ├── api/
│   │   │   └── routes/        # API endpoint handlers
│   │   │       ├── signals.py
│   │   │       ├── markets.py
│   │   │       └── track_record.py
│   │   ├── models/            # Pydantic data models
│   │   │   ├── signal.py      # Core signal model
│   │   │   ├── market.py      # Market model with tiers
│   │   │   ├── news.py        # NewsAPI response models
│   │   │   └── social.py      # Twitter API models
│   │   ├── services/
│   │   │   ├── data_sources/  # External API clients
│   │   │   │   ├── polymarket.py
│   │   │   │   ├── news.py
│   │   │   │   └── social.py
│   │   │   └── signals/       # Signal generation engine
│   │   │       ├── rules.py   # Detection rules
│   │   │       └── generator.py
│   │   ├── db/
│   │   │   └── client.py      # Supabase client wrapper
│   │   ├── config.py          # Settings and env vars
│   │   └── main.py            # FastAPI app entry point
│   ├── tests/
│   └── pyproject.toml         # Python dependencies (uv)
│
├── frontend/                   # Next.js frontend
│   ├── src/
│   │   ├── app/               # Next.js App Router pages
│   │   │   ├── page.tsx       # Dashboard
│   │   │   ├── signals/
│   │   │   ├── markets/
│   │   │   └── track-record/
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   ├── signals/
│   │   │   ├── markets/
│   │   │   ├── track-record/
│   │   │   └── ui/            # shadcn/ui components
│   │   ├── lib/
│   │   │   └── api.ts         # Backend API client
│   │   └── types/
│   │       └── index.ts       # TypeScript interfaces
│   └── package.json
│
├── supabase/
│   └── migrations/
│       └── 001_initial_schema.sql
│
├── SUPABASE_SETUP.md          # Supabase setup guide
└── ARCHITECTURE.md            # This file
```

---

## Backend Architecture

### API Routes

All routes are prefixed with `/api/`:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/signals` | GET | List signals with filters (status, type, pagination) |
| `/api/signals/active` | GET | Get currently active signals |
| `/api/signals/stats` | GET | Get aggregate signal statistics |
| `/api/signals/{id}` | GET | Get single signal by ID |
| `/api/markets` | GET | List markets with filters (tier, active) |
| `/api/markets/{id}` | GET | Get single market by ID |
| `/api/markets/tier/{tier}` | GET | Get markets by tier |
| `/api/track-record` | GET | Get track record summary with stats by type |
| `/api/track-record/history` | GET | Paginated signal history |
| `/api/track-record/export` | GET | CSV download of all signals |
| `/health` | GET | Basic health check |
| `/health/detailed` | GET | Health check with service status |

### Data Source Clients

Each external API has two implementations:
1. **Real client** - Calls the actual API
2. **Mock client** - Returns realistic test data

The mock clients are designed to match the real API response structures exactly, enabling development without API keys and rate limits.

**Polymarket Client** (`services/data_sources/polymarket.py`):
- Fetches markets from Gamma API
- Gets current prices, volumes, liquidity
- Computes market tier based on volume

**News Client** (`services/data_sources/news.py`):
- Fetches articles from NewsAPI
- Extracts sentiment from headlines
- Returns structured article data

**Social Client** (`services/data_sources/social.py`):
- Searches Twitter/X for market mentions
- Calculates mention velocity (mentions per hour)
- Tracks engagement metrics

### Service Layer Pattern

The backend follows a service layer pattern:
- **Routes** handle HTTP concerns (validation, response formatting)
- **Services** contain business logic (signal generation, data aggregation)
- **Clients** handle external API communication
- **Models** define data structures and validation

---

## Frontend Architecture

### Pages

| Route | Component | Purpose |
|-------|-----------|---------|
| `/` | Dashboard | Hero stats, active signals, recent results, email signup |
| `/signals` | SignalsPage | Filterable list of all signals |
| `/markets` | MarketsPage | Browse tracked markets by tier |
| `/track-record` | TrackRecordPage | Full performance transparency |

### Component Hierarchy

```
Layout (Navbar + Footer)
├── Dashboard
│   ├── StatsHero (win rate, avg gain, total signals)
│   ├── ActiveSignals (grid of SignalCards)
│   ├── Recent Results (resolved SignalCards)
│   ├── EmailCapture
│   └── "How It Works" section
│
├── Signals Page
│   ├── Filter buttons (status, type)
│   ├── SignalCard grid
│   └── Pagination
│
├── Markets Page
│   ├── Filter buttons (tier, active signals)
│   ├── MarketCard grid
│   └── Tier legend
│
└── Track Record Page
    ├── StatsHero
    ├── Performance by Signal Type (cards)
    ├── SignalHistory (table with pagination)
    └── Methodology explanation
```

### State Management

The frontend uses React's built-in hooks (`useState`, `useEffect`) for state management. Each page fetches its own data on mount using the API client. No global state management (Redux, Zustand) is needed for the MVP scope.

### API Client

The `lib/api.ts` file provides a typed client for all backend endpoints:

```typescript
export const signalsApi = {
  list: (params) => Promise<SignalListResponse>,
  active: () => Promise<SignalListResponse>,
  stats: () => Promise<SignalStats>,
  get: (id) => Promise<Signal>,
};

export const marketsApi = { ... };
export const trackRecordApi = { ... };
```

### Design System

- **Dark theme** with zinc color palette for trading dashboard aesthetic
- **Green** for BUY signals and wins
- **Red** for SELL signals and losses
- **shadcn/ui components** for consistent, accessible UI elements
- **Responsive grid layouts** that adapt from mobile to desktop

---

## Database Schema

### Core Tables

**`markets`** - Tracked Polymarket markets
- `id` (UUID, PK)
- `condition_id` - Polymarket's unique identifier
- `question` - The market question
- `slug` - URL slug
- `volume`, `volume_24h`, `liquidity` - Trading metrics
- `tier` - Computed tier (THIN, LOW, MEDIUM, HIGH)
- `active`, `closed` - Market status

**`signals`** - Generated trading signals
- `id` (UUID, PK)
- `market_id` (FK to markets)
- `signal_type` - Rule that triggered it
- `direction` - BUY or SELL
- `confidence` - 0.0 to 1.0
- `reasoning` - Human-readable explanation
- `entry_price`, `entry_volume_24h`, etc. - Snapshot at signal time
- `price_1h`, `price_24h`, `price_7d`, `price_at_resolution` - Tracked prices
- `gain_1h_pct`, `gain_24h_pct`, `gain_7d_pct`, `gain_final_pct` - Calculated gains
- `status` - ACTIVE, RESOLVED_WIN, RESOLVED_LOSS, EXPIRED

**`news_sentiment`** - News sentiment snapshots
- `market_id`, `sentiment_score`, `confidence`
- `article_count`, `positive_count`, `negative_count`
- `top_headlines`, `sources`

**`social_mentions`** - Social media activity snapshots
- `market_id`, `mention_count_1h`, `mention_count_24h`
- `mention_velocity`, `velocity_change_pct`
- `top_tweet_ids`

### Database Views

**`signal_stats`** - Aggregate statistics
- Total signals, active, resolved, wins, losses
- Win rate, average gain, best/worst gain

**`signal_stats_by_type`** - Stats grouped by signal type
- Same metrics, partitioned by SENTIMENT_DIVERGENCE, VOLUME_SURGE, etc.

### Row Level Security (RLS)

All tables have RLS enabled:
- `markets`, `signals`, sentiment tables - Public read access
- `profiles`, `user_signal_follows` - Users can only access their own data

---

## Data Flow

### Signal Generation Flow

```
1. Scheduler triggers signal generation (e.g., every 15 minutes)
   │
2. Fetch active markets from Polymarket API
   │
3. For each market:
   ├── Fetch current price/volume from Polymarket
   ├── Fetch news sentiment from NewsAPI
   └── Fetch social mentions from Twitter
   │
4. Run each rule against the market data:
   ├── SentimentDivergenceRule
   ├── VolumeSurgeRule
   ├── SocialSpikeRule
   └── PriceMomentumRule
   │
5. If rule triggers → Create Signal with:
   ├── Market snapshot (price, volume, tier)
   ├── External context (sentiment scores, mention counts)
   ├── Signal metadata (type, direction, confidence, reasoning)
   │
6. Store signal in database
   │
7. (Optional) Send email alerts to subscribers
```

### Signal Tracking Flow

```
1. Background job runs periodically (e.g., hourly)
   │
2. Fetch all ACTIVE signals
   │
3. For each signal:
   ├── Get current market price
   ├── Calculate hours since signal creation
   ├── Update tracking fields (price_1h, gain_1h_pct, etc.)
   │
4. Check for resolution:
   ├── Market closed? → Mark RESOLVED_WIN or RESOLVED_LOSS
   └── Signal expired (e.g., 30 days)? → Mark EXPIRED
```

---

## Signal Generation System

### Market Tiers

Markets are classified by 24-hour volume to filter out illiquid markets:

| Tier | Volume Range | Description |
|------|--------------|-------------|
| THIN | < $10,000 | Too illiquid, skip |
| LOW | $10K - $27K | Low volume, use caution |
| MEDIUM | $27K - $95K | Tradeable |
| HIGH | > $95K | High liquidity, preferred |

### Signal Rules

**1. Sentiment Divergence** (`SENTIMENT_DIVERGENCE`)

Triggers when news sentiment strongly disagrees with market price:
- BUY: Sentiment > 0.3 but price < 0.4 (news bullish, market bearish)
- SELL: Sentiment < -0.3 but price > 0.6 (news bearish, market bullish)

**2. Volume Surge** (`VOLUME_SURGE`)

Triggers when 24h volume spikes significantly (> 3x average) with price movement:
- BUY: Volume surge + price rising
- SELL: Volume surge + price falling

**3. Social Spike** (`SOCIAL_SPIKE`)

Triggers when social media velocity increases dramatically (> 5x normal):
- Direction based on sentiment of mentions

**4. Price Momentum** (`PRICE_MOMENTUM`)

Triggers on sustained price movement with consistent volume:
- BUY: Price trending up consistently
- SELL: Price trending down consistently

### Confidence Scoring

Each signal includes a confidence score (0.0 - 1.0) based on:
- Strength of the triggering condition
- Market liquidity (higher tier = higher confidence)
- Historical accuracy of the rule type

---

## Configuration

### Environment Variables

**Backend** (`.env` file):
```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# External APIs
NEWSAPI_KEY=your_newsapi_key
TWITTER_BEARER_TOKEN=your_twitter_token

# Feature Flags
USE_MOCK_DATA=true  # Set false for production

# Signal Thresholds (optional overrides)
SENTIMENT_DIVERGENCE_THRESHOLD=0.3
VOLUME_SURGE_MULTIPLIER=3.0
SOCIAL_SPIKE_MULTIPLIER=5.0
```

**Frontend** (`.env.local` file):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Settings Class

The backend uses Pydantic's `BaseSettings` for configuration:

```python
class Settings(BaseSettings):
    supabase_url: str
    supabase_anon_key: str
    use_mock_data: bool = True
    sentiment_divergence_threshold: float = 0.3
    # ... etc
```

Settings are loaded from environment variables with optional `.env` file support.

---

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- uv (Python package manager)
- Supabase account

### Backend Setup

```bash
cd polyedge/backend

# Install dependencies
uv sync

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run development server
uv run uvicorn src.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd polyedge/frontend

# Install dependencies
npm install

# Set up environment
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local

# Run development server
npm run dev
```

### Database Setup

See `SUPABASE_SETUP.md` for detailed instructions on:
1. Creating a Supabase project
2. Running the migration script
3. Configuring RLS policies
4. Getting API keys

### Running Tests

```bash
cd polyedge/backend
uv run python -m pytest tests/ -v
```

---

## Design Decisions

### Why Supabase?

- **Managed PostgreSQL** - No database administration needed
- **Built-in Auth** - Ready for user features when needed
- **Row Level Security** - Security at the database level
- **Realtime subscriptions** - Future feature for live updates
- **Generous free tier** - Good for MVP development

### Why Mock Data Services?

Each external API client has a mock implementation because:
- **Development speed** - No API keys needed to start coding
- **Rate limit safety** - Avoid hitting API limits during development
- **Consistent testing** - Mock data is deterministic
- **Structure validation** - Mocks match real API response shapes

### Why Not Redux?

For the MVP scope, React's built-in state management is sufficient:
- Each page fetches its own data
- No complex cross-page state sharing needed
- Simpler mental model for new developers
- Can add Zustand/Redux later if needed

### Why shadcn/ui?

- **Copy-paste components** - Full control over the code
- **Accessible by default** - Built on Radix UI primitives
- **Tailwind integration** - Consistent styling system
- **Dark mode ready** - Easy theme customization

---

## Future Considerations

### Not Yet Implemented

- Background job scheduler for signal generation
- Background job for signal price tracking
- Email notification system (AWS SES)
- User authentication and profiles
- Personal signal tracking (user follows)
- Performance charts with historical data
- Webhook integrations

### Scaling Considerations

- Add Redis for caching market data
- Implement rate limiting on API endpoints
- Add job queue (Celery/RQ) for background tasks
- Consider serverless functions for signal generation
