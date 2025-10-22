from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Buttondown event types"""
    SUBSCRIBER_OPENED = "subscriber.opened"
    SUBSCRIBER_CLICKED = "subscriber.clicked"
    SUBSCRIBER_CONFIRMED = "subscriber.confirmed"
    SUBSCRIBER_DELIVERED = "subscriber.delivered"
    SUBSCRIBER_UNSUBSCRIBED = "subscriber.unsubscribed"
    EMAIL_SENT = "email.sent"

class ButtondownSubscriberData(BaseModel):
    """Subscriber data from Buttondown webhook"""
    subscriber: str = Field(..., description="Buttondown subscriber UUID")
    email: Optional[str] = None

class ButtondownWebhookPayload(BaseModel):
    """Complete webhook payload from Buttondown"""
    event_type: EventType
    data: ButtondownSubscriberData

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "subscriber.opened",
                "data": {
                    "subscriber": "ac79483b-cd28-49c1-982e-8a88e846d7e7"
                }
            }
        }

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

    class Config:
        from_attributes = True
