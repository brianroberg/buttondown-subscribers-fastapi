import pytest
import json
import hmac
import hashlib
import time


def generate_test_signature(payload: dict, secret: str) -> tuple:
    """Generate valid webhook signature for testing"""
    timestamp = str(int(time.time()))
    payload_str = json.dumps(payload)
    signed_content = f"{timestamp}.{payload_str}"

    signature = hmac.new(
        secret.encode('utf-8'),
        signed_content.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    return f"sha256={signature}", timestamp


def test_webhook_health(client):
    """Test webhook health endpoint"""
    response = client.get("/webhooks/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "healthy"


def test_webhook_valid_payload(client, sample_webhook_payload):
    """Test webhook with valid payload"""
    response = client.post(
        "/webhooks/buttondown",
        json=sample_webhook_payload
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["success", "duplicate"]


def test_webhook_invalid_json(client):
    """Test webhook with invalid JSON"""
    response = client.post(
        "/webhooks/buttondown",
        data="invalid json",
        headers={"Content-Type": "application/json"}
    )

    assert response.status_code == 400


def test_webhook_missing_event_type(client):
    """Test webhook with missing event_type"""
    response = client.post(
        "/webhooks/buttondown",
        json={"data": {}}
    )

    assert response.status_code == 400


def test_webhook_duplicate_event(client, sample_webhook_payload):
    """Test duplicate webhook handling"""
    # Send same webhook twice
    response1 = client.post(
        "/webhooks/buttondown",
        json=sample_webhook_payload
    )
    response2 = client.post(
        "/webhooks/buttondown",
        json=sample_webhook_payload
    )

    assert response1.status_code == 200
    assert response2.status_code == 200
    assert response2.json()["status"] == "duplicate"


def test_webhook_subscriber_opened(client, test_db, sample_webhook_payload):
    """Test subscriber.opened event processing"""
    response = client.post(
        "/webhooks/buttondown",
        json=sample_webhook_payload
    )

    assert response.status_code == 200

    # Verify subscriber was created
    from app.models import Subscriber
    subscriber = test_db.query(Subscriber).filter(
        Subscriber.buttondown_id == "test-subscriber-id"
    ).first()

    assert subscriber is not None


def test_webhook_subscriber_clicked(client, test_db):
    """Test subscriber.clicked event processing"""
    payload = {
        "event_type": "subscriber.clicked",
        "data": {
            "subscriber": "test-subscriber-id-2",
            "link": {"url": "https://example.com"}
        }
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200


def test_webhook_unhandled_event_type(client):
    """Test unhandled event type"""
    payload = {
        "event_type": "unknown.event",
        "data": {"subscriber": "test-id"}
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200


def test_webhook_get_validation(client):
    """Test GET request to webhook endpoint (validation)"""
    response = client.get("/webhooks/buttondown")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_webhook_subscriber_confirmed_new(client, test_db):
    """Test subscriber.confirmed event with new subscriber"""
    payload = {
        "event_type": "subscriber.confirmed",
        "data": {
            "subscriber": "confirmed-subscriber",
            "email": "confirmed@example.com"
        }
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200

    from app.models import Subscriber
    subscriber = test_db.query(Subscriber).filter(
        Subscriber.buttondown_id == "confirmed-subscriber"
    ).first()

    assert subscriber is not None
    assert subscriber.status == "active"


def test_webhook_subscriber_confirmed_existing(client, test_db, sample_subscriber):
    """Test subscriber.confirmed event with existing subscriber"""
    # Update subscriber to inactive first
    sample_subscriber.status = "unsubscribed"
    test_db.commit()

    payload = {
        "event_type": "subscriber.confirmed",
        "data": {
            "subscriber": "test-subscriber-id",
            "email": "test@example.com"
        }
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200

    test_db.refresh(sample_subscriber)
    assert sample_subscriber.status == "active"


def test_webhook_subscriber_unsubscribed(client, test_db, sample_subscriber):
    """Test subscriber.unsubscribed event"""
    payload = {
        "event_type": "subscriber.unsubscribed",
        "data": {
            "subscriber": "test-subscriber-id"
        }
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200

    test_db.refresh(sample_subscriber)
    assert sample_subscriber.status == "unsubscribed"


def test_webhook_missing_subscriber_id(client):
    """Test webhook with missing subscriber ID"""
    payload = {
        "event_type": "subscriber.opened",
        "data": {}
    }

    response = client.post("/webhooks/buttondown", json=payload)
    # Should still return 200 (logged warning but no error)
    assert response.status_code == 200


def test_webhook_subscriber_clicked_new(client, test_db):
    """Test subscriber.clicked event creating new subscriber"""
    payload = {
        "event_type": "subscriber.clicked",
        "data": {
            "subscriber": "new-clicker",
            "email": "clicker@example.com",
            "link": "https://example.com/page"
        }
    }

    response = client.post("/webhooks/buttondown", json=payload)
    assert response.status_code == 200

    from app.models import Subscriber
    subscriber = test_db.query(Subscriber).filter(
        Subscriber.buttondown_id == "new-clicker"
    ).first()

    assert subscriber is not None
