"""FastAPI application factory."""

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import signals, markets, track_record, health, subscriptions, tracking
from src.config import get_settings

logger = logging.getLogger(__name__)


async def tracking_background_task():
    """Run tracking updates periodically in the background."""
    from src.services.tracking import get_tracker, set_last_tracking_run

    settings = get_settings()
    logger.info(
        f"Background tracking started (enabled={settings.tracking_enabled}, "
        f"interval={settings.tracking_interval_minutes}min)"
    )

    # Wait a bit before first run to let the app fully start
    await asyncio.sleep(10)

    while True:
        try:
            if settings.tracking_enabled:
                logger.info("Running scheduled tracking update...")
                tracker = get_tracker()
                updated_count = await tracker.update_all_active_signals()
                expired_count = await tracker.expire_stale_signals(settings.tracking_expire_days)
                set_last_tracking_run(datetime.utcnow())
                logger.info(
                    f"Scheduled tracking complete: {updated_count} signals updated, "
                    f"{expired_count} signals expired"
                )
        except Exception as e:
            logger.error(f"Error in background tracking task: {e}")

        # Wait for next interval
        await asyncio.sleep(settings.tracking_interval_minutes * 60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - start/stop background tasks."""
    settings = get_settings()

    # Start background tracking task
    tracking_task = None
    if settings.tracking_enabled:
        tracking_task = asyncio.create_task(tracking_background_task())
        logger.info("Background tracking task started")

    yield

    # Cleanup on shutdown
    if tracking_task:
        tracking_task.cancel()
        try:
            await tracking_task
        except asyncio.CancelledError:
            pass
        logger.info("Background tracking task stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="PolyEdge API",
        description="Your edge in prediction markets - Trade signals and market intelligence",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",  # Next.js dev
            "http://localhost:5173",  # Vite dev
            "https://polyedge.io",    # Production
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
    app.include_router(markets.router, prefix="/api/markets", tags=["Markets"])
    app.include_router(track_record.router, prefix="/api/track-record", tags=["Track Record"])
    app.include_router(subscriptions.router, prefix="/api/subscriptions", tags=["Subscriptions"])
    app.include_router(tracking.router, prefix="/api/tracking", tags=["Tracking"])

    return app


# Create app instance for uvicorn
app = create_app()
