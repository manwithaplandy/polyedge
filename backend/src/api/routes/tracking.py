"""Signal tracking API endpoints."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.config import get_settings
from src.db.client import get_supabase_client
from src.services.tracking import get_tracker, get_last_tracking_run, set_last_tracking_run

router = APIRouter()
logger = logging.getLogger(__name__)


class TrackingUpdateDetail(BaseModel):
    """Detail for a single signal update."""

    signal_id: str
    status: str  # "updated", "resolved", "expired", "error"
    current_gain_pct: Optional[float] = None
    final_gain_pct: Optional[float] = None
    error: Optional[str] = None


class TrackingUpdateResponse(BaseModel):
    """Response from a tracking update."""

    signals_updated: int
    signals_resolved: int
    signals_expired: int
    errors: int
    update_time: str
    details: list[TrackingUpdateDetail]


class TrackingStatusResponse(BaseModel):
    """Status of the tracking service."""

    tracking_enabled: bool
    interval_minutes: int
    last_update: Optional[str]
    next_update: Optional[str]
    active_signals: int
    expire_after_days: int


class SingleSignalUpdateResponse(BaseModel):
    """Response for single signal update."""

    signal_id: str
    status: str
    entry_price: float
    current_price: Optional[float]
    current_gain_pct: Optional[float]
    gain_1h_pct: Optional[float]
    gain_24h_pct: Optional[float]
    gain_7d_pct: Optional[float]
    gain_final_pct: Optional[float]
    hours_since_signal: float


@router.post("/update", response_model=TrackingUpdateResponse)
async def trigger_tracking_update():
    """
    Trigger a manual tracking update for all active signals.

    This fetches current market prices and updates gain percentages
    for all active signals. Useful for immediate updates without
    waiting for the background scheduler.
    """
    settings = get_settings()
    tracker = get_tracker()
    db = get_supabase_client()

    # Get active signals
    active_signals = await db.get_active_signals()

    details = []
    signals_updated = 0
    signals_resolved = 0
    signals_expired = 0
    errors = 0

    for signal in active_signals:
        try:
            original_status = signal.status.value
            updated_signal = await tracker.update_signal_tracking(signal)

            detail = TrackingUpdateDetail(
                signal_id=str(signal.id),
                status="updated",
            )

            # Check if signal was resolved
            if updated_signal.status.value != original_status:
                if "RESOLVED" in updated_signal.status.value:
                    detail.status = "resolved"
                    detail.final_gain_pct = updated_signal.gain_final_pct
                    signals_resolved += 1
                elif updated_signal.status.value == "EXPIRED":
                    detail.status = "expired"
                    signals_expired += 1
            else:
                # Calculate current gain for response
                current_gain = None
                if updated_signal.gain_7d_pct is not None:
                    current_gain = updated_signal.gain_7d_pct
                elif updated_signal.gain_24h_pct is not None:
                    current_gain = updated_signal.gain_24h_pct
                elif updated_signal.gain_1h_pct is not None:
                    current_gain = updated_signal.gain_1h_pct
                detail.current_gain_pct = current_gain
                signals_updated += 1

            details.append(detail)

        except Exception as e:
            logger.error(f"Error updating signal {signal.id}: {e}")
            details.append(TrackingUpdateDetail(
                signal_id=str(signal.id),
                status="error",
                error=str(e),
            ))
            errors += 1

    # Also run expiration check
    expired_count = await tracker.expire_stale_signals(settings.tracking_expire_days)
    signals_expired += expired_count

    # Update last run timestamp
    update_time = datetime.now(timezone.utc)
    set_last_tracking_run(update_time)

    logger.info(
        f"Tracking update complete: {signals_updated} updated, "
        f"{signals_resolved} resolved, {signals_expired} expired, {errors} errors"
    )

    return TrackingUpdateResponse(
        signals_updated=signals_updated,
        signals_resolved=signals_resolved,
        signals_expired=signals_expired,
        errors=errors,
        update_time=update_time.isoformat(),
        details=details,
    )


@router.get("/status", response_model=TrackingStatusResponse)
async def get_tracking_status():
    """
    Get the current status of the tracking service.

    Returns configuration, last run time, and count of active signals.
    """
    settings = get_settings()
    db = get_supabase_client()

    # Get active signal count
    active_signals = await db.get_active_signals()
    active_count = len(active_signals)

    # Calculate next update time
    last_run = get_last_tracking_run()
    next_update = None
    if last_run and settings.tracking_enabled:
        next_update = last_run + timedelta(minutes=settings.tracking_interval_minutes)

    return TrackingStatusResponse(
        tracking_enabled=settings.tracking_enabled,
        interval_minutes=settings.tracking_interval_minutes,
        last_update=last_run.isoformat() if last_run else None,
        next_update=next_update.isoformat() if next_update else None,
        active_signals=active_count,
        expire_after_days=settings.tracking_expire_days,
    )


@router.post("/update/{signal_id}", response_model=SingleSignalUpdateResponse)
async def update_single_signal(signal_id: str):
    """
    Update tracking for a single signal.

    Fetches current market price and updates the signal's gain fields.
    Returns detailed tracking information.
    """
    tracker = get_tracker()
    db = get_supabase_client()

    # Get the signal
    try:
        signal_uuid = UUID(signal_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid signal ID format")

    signal = await db.get_signal(signal_uuid)
    if not signal:
        raise HTTPException(status_code=404, detail="Signal not found")

    # Update tracking
    try:
        updated_signal = await tracker.update_signal_tracking(signal)
    except Exception as e:
        logger.error(f"Error updating signal {signal_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error updating signal: {str(e)}")

    # Calculate hours since signal
    created_at = updated_signal.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    hours_since = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600

    # Get the most recent gain for current_gain_pct
    current_gain = None
    current_price = None

    if updated_signal.price_at_resolution is not None:
        current_price = updated_signal.price_at_resolution
        current_gain = updated_signal.gain_final_pct
    elif updated_signal.price_7d is not None:
        current_price = updated_signal.price_7d
        current_gain = updated_signal.gain_7d_pct
    elif updated_signal.price_24h is not None:
        current_price = updated_signal.price_24h
        current_gain = updated_signal.gain_24h_pct
    elif updated_signal.price_1h is not None:
        current_price = updated_signal.price_1h
        current_gain = updated_signal.gain_1h_pct

    return SingleSignalUpdateResponse(
        signal_id=str(updated_signal.id),
        status=updated_signal.status.value,
        entry_price=updated_signal.entry_price,
        current_price=current_price,
        current_gain_pct=current_gain,
        gain_1h_pct=updated_signal.gain_1h_pct,
        gain_24h_pct=updated_signal.gain_24h_pct,
        gain_7d_pct=updated_signal.gain_7d_pct,
        gain_final_pct=updated_signal.gain_final_pct,
        hours_since_signal=round(hours_since, 2),
    )
