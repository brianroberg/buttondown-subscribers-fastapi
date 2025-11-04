from typing import Optional, Literal, TYPE_CHECKING
from datetime import datetime, date

from pydantic import BaseModel, EmailStr, ConfigDict

if TYPE_CHECKING:
    from app.services.buttondown_sync import SyncOutcome
class SubscriberBase(BaseModel):
    """Base subscriber schema"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Literal["active", "unsubscribed", "bounced"] = "active"

class SubscriberCreate(SubscriberBase):
    """Schema for creating a subscriber"""
    buttondown_id: str

class SubscriberInDB(SubscriberBase):
    """Schema for subscriber from database"""
    id: int
    buttondown_id: str
    subscription_date: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Dashboard response schemas

class DashboardStats(BaseModel):
    """Overall dashboard statistics"""
    total_subscribers: int
    active_subscribers: int
    total_opens: int
    total_clicks: int
    engagement_rate: float
    period_start: datetime
    period_end: datetime

class TopSubscriber(BaseModel):
    """Top engaged subscriber"""
    subscriber_id: int
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    total_opens: int
    total_clicks: int
    total_engagement: int

class EngagementTrend(BaseModel):
    """Daily engagement trend"""
    date: date
    opens: int
    clicks: int
    total: int

class EventResponse(BaseModel):
    """Event response schema"""
    id: int
    event_type: str
    created_at: datetime
    event_metadata: Optional[dict] = None

    model_config = ConfigDict(from_attributes=True)


class SyncResponse(BaseModel):
    """Response returned after running a sync."""

    events_created: int
    events_skipped: int
    subscribers_created: int
    subscribers_updated: int
    requested_since: Optional[datetime] = None
    effective_since: Optional[datetime] = None
    latest_event_at: Optional[datetime] = None
    last_synced_at: Optional[datetime] = None

    @classmethod
    def from_outcome(cls, outcome: "SyncOutcome") -> "SyncResponse":
        return cls(
            events_created=outcome.events_created,
            events_skipped=outcome.events_skipped,
            subscribers_created=outcome.subscribers_created,
            subscribers_updated=outcome.subscribers_updated,
            requested_since=outcome.requested_since,
            effective_since=outcome.effective_since,
            latest_event_at=outcome.latest_event_at,
            last_synced_at=outcome.last_synced_at,
        )


class SyncStateResponse(BaseModel):
    """Current sync cursor information."""

    last_synced_at: Optional[datetime]
    default_lookback_days: int
    pending_initial_sync: bool
