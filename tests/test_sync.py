from datetime import datetime, timedelta, timezone

from app.main import app
from app.models import Event, Subscriber, SyncState
from app.utils.buttondown import get_buttondown_client


class FakeButtondownAPI:
    """Simple stand-in for the Buttondown API client."""

    def __init__(self, events):
        self.events = events
        self.calls = []

    def iter_events(self, *, since=None, expand=None, ordering=None):
        self.calls.append({"since": since, "expand": expand, "ordering": ordering})
        for event in self.events:
            yield event


def make_event(
    event_id: str,
    event_type: str,
    created_at: datetime,
    subscriber_id: str = "sub-1",
    email: str = "alice@example.com",
    link: str = "https://example.com",
):
    return {
        "id": event_id,
        "event_type": event_type,
        "creation_date": created_at.isoformat(),
        "subscriber_id": subscriber_id,
        "subscriber": {
            "id": subscriber_id,
            "email_address": email,
            "first_name": "Alice",
            "last_name": "Example",
            "source": "api",
        },
        "metadata": {"url": link},
    }


def parse_utc(timestamp: str) -> datetime:
    dt = datetime.fromisoformat(timestamp)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def test_sync_creates_events_and_subscribers(client, test_db):
    """POST /api/sync/events should persist new events and subscribers."""
    created_at = datetime.now(timezone.utc).replace(microsecond=0)
    events = [
        make_event("evt-1", "opened", created_at),
        make_event("evt-2", "clicked", created_at + timedelta(hours=1)),
    ]
    fake_api = FakeButtondownAPI(events)
    app.dependency_overrides[get_buttondown_client] = lambda: fake_api

    try:
        response = client.post("/api/sync/events")
    finally:
        app.dependency_overrides.pop(get_buttondown_client, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["events_created"] == 2
    assert payload["subscribers_created"] == 1
    assert parse_utc(payload["last_synced_at"]) == parse_utc(events[-1]["creation_date"])

    subscribers = test_db.query(Subscriber).all()
    assert len(subscribers) == 1
    subscriber = subscribers[0]
    assert subscriber.email == "alice@example.com"
    assert subscriber.status == "active"

    stored_events = test_db.query(Event).order_by(Event.created_at).all()
    assert [event.event_type for event in stored_events] == [
        "subscriber.opened",
        "subscriber.clicked",
    ]
    assert stored_events[0].link_url == "https://example.com"

    state = (
        test_db.query(SyncState)
        .filter(SyncState.key == "buttondown_events")
        .first()
    )
    assert state is not None
    assert state.last_synced_at is not None


def test_sync_skips_existing_events(client, test_db):
    """Repeated sync runs should not duplicate events."""
    created_at = datetime.now(timezone.utc).replace(microsecond=0)
    events = [make_event("evt-3", "opened", created_at)]
    fake_api = FakeButtondownAPI(events)
    app.dependency_overrides[get_buttondown_client] = lambda: fake_api

    try:
        first = client.post("/api/sync/events")
        second = client.post("/api/sync/events")
    finally:
        app.dependency_overrides.pop(get_buttondown_client, None)

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["events_created"] == 0
    assert parse_utc(second_payload["effective_since"]) == parse_utc(first.json()["last_synced_at"])

    events_in_db = test_db.query(Event).all()
    assert len(events_in_db) == 1


def test_sync_state_endpoint(client, test_db):
    """GET /api/sync/events/state should report the current watermark."""
    created_at = datetime.now(timezone.utc).replace(microsecond=0)
    events = [make_event("evt-4", "clicked", created_at)]
    fake_api = FakeButtondownAPI(events)
    app.dependency_overrides[get_buttondown_client] = lambda: fake_api

    try:
        client.post("/api/sync/events")
    finally:
        app.dependency_overrides.pop(get_buttondown_client, None)

    response = client.get("/api/sync/events/state")
    assert response.status_code == 200
    data = response.json()
    assert parse_utc(data["last_synced_at"]) == created_at
    assert data["pending_initial_sync"] is False
