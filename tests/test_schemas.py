import pytest
from datetime import datetime, timezone
from pydantic import ValidationError

from app.schemas import (
    SubscriberCreate,
    SubscriberInDB,
    SyncResponse,
    SyncStateResponse,
)
from app.services.buttondown_sync import SyncOutcome


def test_subscriber_create_valid():
    """Test valid SubscriberCreate schema"""
    subscriber = SubscriberCreate(
        buttondown_id="btn-123",
        email="test@example.com",
        first_name="John",
        last_name="Doe",
        status="active"
    )
    assert subscriber.buttondown_id == "btn-123"
    assert subscriber.email == "test@example.com"
    assert subscriber.first_name == "John"
    assert subscriber.last_name == "Doe"
    assert subscriber.status == "active"


def test_subscriber_create_minimal():
    """Test SubscriberCreate with minimal fields"""
    subscriber = SubscriberCreate(buttondown_id="btn-minimal")
    assert subscriber.buttondown_id == "btn-minimal"
    assert subscriber.email is None
    assert subscriber.status == "active"  # default


def test_subscriber_create_invalid_status():
    """Test SubscriberCreate with invalid status"""
    with pytest.raises(ValidationError):
        SubscriberCreate(
            buttondown_id="btn-123",
            status="invalid_status"
        )


def test_subscriber_create_invalid_email():
    """Test SubscriberCreate with invalid email"""
    with pytest.raises(ValidationError):
        SubscriberCreate(
            buttondown_id="btn-123",
            email="not-an-email"
        )


def test_subscriber_in_db_from_orm():
    """Test SubscriberInDB schema with ORM model"""
    # This tests the from_attributes configuration
    class MockSubscriber:
        id = 1
        buttondown_id = "btn-789"
        email = "orm@example.com"
        first_name = "ORM"
        last_name = "Test"
        status = "active"
        subscription_date = datetime.now()
        created_at = datetime.now()

    subscriber = SubscriberInDB.model_validate(MockSubscriber())
    assert subscriber.id == 1
    assert subscriber.buttondown_id == "btn-789"
    assert subscriber.email == "orm@example.com"


def test_sync_response_from_outcome():
    """SyncResponse should mirror SyncOutcome values."""
    timestamp = datetime.now(timezone.utc)
    outcome = SyncOutcome(
        events_created=5,
        events_skipped=1,
        subscribers_created=2,
        subscribers_updated=3,
        requested_since=timestamp,
        effective_since=timestamp,
        latest_event_at=timestamp,
        last_synced_at=timestamp,
    )

    response = SyncResponse.from_outcome(outcome)
    assert response.events_created == 5
    assert response.events_skipped == 1
    assert response.subscribers_created == 2
    assert response.latest_event_at == timestamp


def test_sync_state_response_defaults():
    """SyncStateResponse should expose default values."""
    result = SyncStateResponse(
        last_synced_at=None,
        default_lookback_days=30,
        pending_initial_sync=True,
    )
    assert result.pending_initial_sync is True
    assert result.default_lookback_days == 30
