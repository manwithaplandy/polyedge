# PolyEdge Backend

**Your edge in prediction markets.** Trade signals powered by news sentiment, social activity, and market dynamics.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- Supabase account (for production)

### Setup

1. **Install dependencies:**

```bash
cd polyedge/backend
uv sync
# or: pip install -e ".[dev]"
```

2. **Configure environment:**

```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run database migrations:**

In your Supabase SQL editor, run the migration file:
```
supabase/migrations/001_initial_schema.sql
```

4. **Start the development server:**

```bash
uv run uvicorn src.api.app:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

### API Documentation

With `DEBUG=true`, interactive docs are available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development Mode

By default, the backend runs with `USE_MOCK_DATA=true`, which:

- Uses mock market data (no Polymarket API calls)
- Uses mock news headlines with sentiment
- Uses mock social mention data
- Returns realistic demo statistics

This allows full development without any API keys.

## Core Endpoints

### Signals

- `GET /api/signals` - List all signals
- `GET /api/signals/active` - Get active signals only
- `GET /api/signals/stats` - Aggregate performance stats
- `GET /api/signals/{id}` - Get single signal

### Markets

- `GET /api/markets` - List markets with our analysis
- `GET /api/markets/{id}` - Single market detail
- `GET /api/markets/tier/{tier}` - Markets by volume tier

### Track Record

- `GET /api/track-record` - Full performance summary
- `GET /api/track-record/history` - Signal history with pagination
- `GET /api/track-record/export` - CSV export

### Health

- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed service status

## Architecture

```
src/
├── api/                    # FastAPI routes
│   ├── app.py             # Application factory
│   └── routes/            # Route modules
├── db/                     # Supabase client
│   └── client.py          # Database operations
├── models/                 # Pydantic models
│   ├── market.py          # Market data models
│   ├── signal.py          # Signal models (core!)
│   ├── news.py            # News/sentiment models
│   └── social.py          # Social data models
├── services/
│   ├── data_sources/      # API clients (real + mock)
│   │   ├── polymarket.py  # Polymarket Gamma API
│   │   ├── news.py        # NewsAPI.org
│   │   └── social.py      # Twitter/X API
│   ├── signals/           # Signal generation
│   │   ├── generator.py   # Main orchestrator
│   │   └── rules.py       # Signal detection rules
│   └── tracking/          # Performance tracking
│       └── tracker.py     # Updates signal outcomes
└── config.py              # Settings management
```

## Signal Types

1. **Sentiment Divergence** - News sentiment diverges from market price
2. **Volume Surge** - Trading volume spikes with price movement
3. **Social Spike** - Social mentions surge with strong sentiment
4. **Price Momentum** - Significant price movement with volume confirmation

## Testing

```bash
uv run pytest
# With coverage:
uv run pytest --cov=src
```

## Production Deployment

1. Set `USE_MOCK_DATA=false`
2. Configure Supabase credentials
3. Add NewsAPI and Twitter API keys
4. Set up AWS SES for email alerts
5. Deploy to your preferred platform (Railway, Fly.io, etc.)

## License

Proprietary - PolyEdge
