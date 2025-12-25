"""Email subscription API endpoints."""

import re
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr, field_validator

from src.config import get_settings
from src.db.client import get_supabase_client

router = APIRouter()


class SubscriptionRequest(BaseModel):
    """Request body for email subscription."""

    email: str
    source: Optional[str] = "website"

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower().strip()


class SubscriptionResponse(BaseModel):
    """Response for subscription endpoints."""

    success: bool
    message: str
    email: Optional[str] = None


@router.post("", response_model=SubscriptionResponse)
async def subscribe(request: SubscriptionRequest):
    """Subscribe an email address to alerts."""
    settings = get_settings()

    # In mock mode, just return success
    if settings.use_mock_data:
        return SubscriptionResponse(
            success=True,
            message="Successfully subscribed to alerts",
            email=request.email,
        )

    try:
        db = get_supabase_client()

        # Insert the subscription
        result = db._client.table("email_subscriptions").upsert(
            {
                "email": request.email,
                "source": request.source,
                "is_active": True,
            },
            on_conflict="email",
        ).execute()

        if result.data:
            return SubscriptionResponse(
                success=True,
                message="Successfully subscribed to alerts",
                email=request.email,
            )
        else:
            raise HTTPException(status_code=500, detail="Failed to save subscription")

    except HTTPException:
        raise
    except Exception as e:
        # Check for unique constraint violation (already subscribed)
        if "duplicate" in str(e).lower() or "unique" in str(e).lower():
            return SubscriptionResponse(
                success=True,
                message="You're already subscribed",
                email=request.email,
            )
        raise HTTPException(status_code=500, detail=f"Subscription failed: {str(e)}")
