import pytest
from pydantic import ValidationError
from app.schemas import (
    EventType,
    ButtondownSubscriberData,
    ButtondownWebhookPayload,
    SubscriberCreate,
    SubscriberInDB,
)
from datetime import datetime


def test_event_type_enum():
    """Test EventType enum values"""
    assert EventType.SUBSCRIBER_OPENED == "subscriber.opened"
    assert EventType.SUBSCRIBER_CLICKED == "subscriber.clicked"
    assert EventType.SUBSCRIBER_CONFIRMED == "subscriber.confirmed"
    assert EventType.SUBSCRIBER_DELIVERED == "subscriber.delivered"
    assert EventType.SUBSCRIBER_UNSUBSCRIBED == "subscriber.unsubscribed"
    assert EventType.EMAIL_SENT == "email.sent"


def test_buttondown_subscriber_data_valid():
    """Test valid ButtondownSubscriberData"""
    data = ButtondownSubscriberData(
        subscriber="test-uuid-123",
        email="test@example.com"
    )
    assert data.subscriber == "test-uuid-123"
    assert data.email == "test@example.com"


def test_buttondown_subscriber_data_without_email():
    """Test ButtondownSubscriberData without email (optional)"""
    data = ButtondownSubscriberData(subscriber="test-uuid-123")
    assert data.subscriber == "test-uuid-123"
    assert data.email is None


def test_buttondown_webhook_payload_valid():
    """Test valid ButtondownWebhookPayload"""
    payload = ButtondownWebhookPayload(
        event_type=EventType.SUBSCRIBER_OPENED,
        data=ButtondownSubscriberData(subscriber="test-uuid")
    )
    assert payload.event_type == EventType.SUBSCRIBER_OPENED
    assert payload.data.subscriber == "test-uuid"


def test_buttondown_webhook_payload_from_dict():
    """Test creating ButtondownWebhookPayload from dict"""
    payload_dict = {
        "event_type": "subscriber.clicked",
        "data": {
            "subscriber": "test-uuid-456",
            "email": "user@example.com"
        }
    }
    payload = ButtondownWebhookPayload(**payload_dict)
    assert payload.event_type == EventType.SUBSCRIBER_CLICKED
    assert payload.data.subscriber == "test-uuid-456"
    assert payload.data.email == "user@example.com"


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
