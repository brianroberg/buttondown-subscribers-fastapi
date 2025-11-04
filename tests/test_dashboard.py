from datetime import datetime, timedelta

from app.models import Subscriber, Event


def create_sample_data(db):
    subscriber = Subscriber(
        buttondown_id="subscriber-123",
        email="sample@example.com",
        first_name="Sample",
        last_name="User",
        status="active",
    )
    db.add(subscriber)
    db.commit()
    db.refresh(subscriber)

    events = [
        Event(
            event_id="evt-open",
            subscriber_id=subscriber.id,
            event_type="subscriber.opened",
            created_at=datetime.utcnow() - timedelta(days=1),
        ),
        Event(
            event_id="evt-click",
            subscriber_id=subscriber.id,
            event_type="subscriber.clicked",
            created_at=datetime.utcnow(),
        ),
    ]
    db.add_all(events)
    db.commit()

    return subscriber


def test_dashboard_stats(client, test_db):
    create_sample_data(test_db)

    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_subscribers"] == 1
    assert payload["total_opens"] == 1
    assert payload["total_clicks"] == 1


def test_dashboard_top_subscribers(client, test_db):
    create_sample_data(test_db)

    response = client.get("/api/dashboard/subscribers/top")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["total_opens"] == 1
    assert payload[0]["total_clicks"] == 1


def test_dashboard_trends(client, test_db):
    create_sample_data(test_db)

    response = client.get("/api/dashboard/trends", params={"days": 7})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) >= 1


def test_dashboard_subscriber_events(client, test_db):
    subscriber = create_sample_data(test_db)

    response = client.get(f"/api/dashboard/subscribers/{subscriber.id}/events")
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 2
