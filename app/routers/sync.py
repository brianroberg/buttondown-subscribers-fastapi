from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import SyncState
from app.schemas import SyncResponse, SyncStateResponse
from app.services.buttondown_sync import ButtondownEventSynchronizer
from app.utils.buttondown import ButtondownAPI, ButtondownAPIError, get_buttondown_client

router = APIRouter(prefix="/api/sync", tags=["sync"])
settings = get_settings()


@router.post("/events", response_model=SyncResponse)
def sync_buttondown_events(
    since: Optional[datetime] = Query(
        default=None,
        description="Optional timestamp to force syncing events created after this moment.",
    ),
    db: Session = Depends(get_db),
    client: ButtondownAPI = Depends(get_buttondown_client),
) -> SyncResponse:
    """Trigger an on-demand synchronisation run."""
    try:
        synchronizer = ButtondownEventSynchronizer(
            db,
            client,
            default_lookback_days=settings.buttondown_initial_sync_lookback_days,
        )
        outcome = synchronizer.sync(since=since)
    except ButtondownAPIError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return SyncResponse.from_outcome(outcome)


@router.get("/events/state", response_model=SyncStateResponse)
def get_sync_state(
    db: Session = Depends(get_db),
) -> SyncStateResponse:
    """Return the persisted synchronisation watermark."""
    state = (
        db.query(SyncState)
        .filter(SyncState.key == ButtondownEventSynchronizer.STATE_KEY)
        .first()
    )
    return SyncStateResponse(
        last_synced_at=state.last_synced_at if state else None,
        default_lookback_days=settings.buttondown_initial_sync_lookback_days,
        pending_initial_sync=state is None or state.last_synced_at is None,
    )
