# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PolyEdge is an AI-powered trading signal platform for Polymarket prediction markets. The system monitors markets, correlates data with news sentiment and social media activity, and generates BUY/SELL signals with transparent track records. Every signal records entry price, volume data, and tracks performance over time (1h, 24h, 7d, and final resolution).

## Development Commands

### Backend (Python 3.11+ with uv)
```bash
cd backend
uv sync                                              # Install dependencies
uv run uvicorn src.api.app:app --reload --port 8000  # Dev server
uv run pytest tests/ -v                              # Run all tests
uv run pytest tests/test_file.py::test_name -v      # Run single test
uv run black src/                                    # Format code
uv run ruff check src/                               # Lint
uv run mypy src/                                     # Type check
```

### Frontend (Next.js 14 with npm)
```bash
cd frontend
npm install          # Install dependencies
npm run dev          # Dev server (http://localhost:3000)
npm run build        # Production build
npm run lint         # ESLint
```

## Architecture

```
backend/
├── src/
│   ├── api/routes/          # FastAPI endpoints (/signals, /markets, /track-record)
│   ├── services/
│   │   ├── signals/         # Signal generation engine with 4 rule types
│   │   └── data_sources/    # External APIs (Polymarket, NewsAPI, Twitter)
│   ├── models/              # Pydantic models (Signal, Market, NewsSentiment)
│   ├── db/                  # Supabase PostgreSQL wrapper
│   └── config.py            # Environment configuration
frontend/
├── src/
│   ├── app/                 # Next.js App Router pages (/, /signals, /markets, /track-record)
│   ├── components/          # React components with shadcn/ui
│   └── lib/api.ts           # Typed API client
supabase/migrations/         # PostgreSQL schema
```

### Signal Generation System

Four signal types in `backend/src/services/signals/rules.py`:
- **SENTIMENT_DIVERGENCE** - News sentiment vs market price divergence
- **VOLUME_SURGE** - Trading volume spike with price movement
- **SOCIAL_SPIKE** - Social media mentions surge with sentiment
- **PRICE_MOMENTUM** - Significant sustained price movement

Each rule extends `SignalRule` base class and returns `SignalCandidate` objects with confidence scores (0.0-1.0).

### Data Flow

1. Data sources fetch from Polymarket (Gamma API), NewsAPI, and Twitter/X
2. Signal rules evaluate market state against thresholds
3. Generated signals stored in Supabase with entry price snapshots
4. Frontend fetches via FastAPI endpoints with filtering/pagination

### Mock-First Development

Every external API has real + mock implementations in `src/services/data_sources/`. Set `USE_MOCK_DATA=true` in backend `.env` to develop without API keys. Mock data matches real response shapes exactly.

## Key Patterns

- **Service Layer**: Routes handle HTTP, services contain business logic, clients handle external APIs
- **Market Tiering**: THIN/LOW/MEDIUM/HIGH based on volume for liquidity filtering
- **Immutable Signals**: Audit trail with performance tracked at 1h, 24h, 7d, resolution intervals
- **Type Safety**: Pydantic models (backend) and TypeScript interfaces (frontend) with strict validation

## Configuration

Backend `.env` key variables:
- `USE_MOCK_DATA=true/false` - Toggle mock vs real external APIs
- `SUPABASE_URL`, `SUPABASE_ANON_KEY` - Database connection
- Signal thresholds: `SENTIMENT_DIVERGENCE_THRESHOLD`, `VOLUME_SURGE_MULTIPLIER`, etc.

Frontend `.env.local`:
- `NEXT_PUBLIC_API_URL=http://localhost:8000` - Backend URL

## API Documentation

With backend running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
