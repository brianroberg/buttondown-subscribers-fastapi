import pytest
from app.models import Subscriber, Event, Tag, SubscriberTag
from datetime import datetime


def test_create_subscriber(test_db):
    """Test creating a subscriber"""
    subscriber = Subscriber(
        buttondown_id="test-id",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    test_db.add(subscriber)
    test_db.commit()
    test_db.refresh(subscriber)

    assert subscriber.id is not None
    assert subscriber.email == "test@example.com"
    assert subscriber.status == "active"


def test_subscriber_unique_email(test_db):
    """Test unique constraint on email"""
    subscriber1 = Subscriber(
        buttondown_id="test-id-1",
        email="test@example.com"
    )
    subscriber2 = Subscriber(
        buttondown_id="test-id-2",
        email="test@example.com"
    )

    test_db.add(subscriber1)
    test_db.commit()

    test_db.add(subscriber2)
    with pytest.raises(Exception):  # IntegrityError
        test_db.commit()


def test_create_event(test_db, sample_subscriber):
    """Test creating an event"""
    event = Event(
        event_id="test-event-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened",
        metadata={"test": "data"}
    )
    test_db.add(event)
    test_db.commit()
    test_db.refresh(event)

    assert event.id is not None
    assert event.subscriber_id == sample_subscriber.id


def test_event_unique_constraint(test_db, sample_subscriber):
    """Test unique constraint on event_id"""
    event1 = Event(
        event_id="duplicate-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened"
    )
    event2 = Event(
        event_id="duplicate-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened"
    )

    test_db.add(event1)
    test_db.commit()

    test_db.add(event2)
    with pytest.raises(Exception):
        test_db.commit()


def test_subscriber_events_relationship(test_db, sample_subscriber):
    """Test relationship between subscriber and events"""
    event = Event(
        event_id="test-event",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.clicked"
    )
    test_db.add(event)
    test_db.commit()

    assert len(sample_subscriber.events) == 1
    assert sample_subscriber.events[0].event_type == "subscriber.clicked"


def test_subscriber_tags_relationship(test_db, sample_subscriber):
    """Test many-to-many relationship with tags"""
    tag = Tag(name="vip", description="VIP subscribers")
    test_db.add(tag)
    test_db.commit()

    subscriber_tag = SubscriberTag(
        subscriber_id=sample_subscriber.id,
        tag_id=tag.id
    )
    test_db.add(subscriber_tag)
    test_db.commit()

    test_db.refresh(sample_subscriber)
    assert len(sample_subscriber.tags) == 1
    assert sample_subscriber.tags[0].name == "vip"
