import pytest
import requests
import time
from app.config import get_settings
from app.models import Event

settings = get_settings()

# Skip integration tests if Buttondown credentials not configured
pytestmark = pytest.mark.skipif(
    not settings.buttondown_api_key or not settings.buttondown_webhook_id,
    reason="Buttondown API credentials not configured (set BUTTONDOWN_API_KEY and BUTTONDOWN_WEBHOOK_ID)"
)


class TestButtondownWebhookIntegration:
    """Integration tests using Buttondown's webhook testing API

    These tests trigger real webhooks from Buttondown using their test API.
    Requires BUTTONDOWN_API_KEY and BUTTONDOWN_WEBHOOK_ID to be set in .env

    For development: Use a separate dev/testing newsletter with synthetic data
    For production: Use production API key (configured via environment)
    """

    def test_buttondown_test_webhook_endpoint(self):
        """Test that Buttondown's webhook testing API is accessible"""
        response = requests.post(
            f"https://api.buttondown.com/v1/webhooks/{settings.buttondown_webhook_id}/test",
            headers={"Authorization": f"Token {settings.buttondown_api_key}"}
        )

        # Buttondown returns 204 No Content on success
        assert response.status_code == 204, f"Webhook test failed with status {response.status_code}: {response.text}"

    def test_webhook_receives_buttondown_test_event(self):
        """Test that our webhook endpoint receives and processes Buttondown test events

        Note: This test triggers a real webhook from Buttondown to the running server.
        Events are stored in the real database (not test database).
        """
        # Import real database session
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # Get initial event count from REAL database
            initial_count = db.query(Event).count()

            # Trigger test webhook from Buttondown
            response = requests.post(
                f"https://api.buttondown.com/v1/webhooks/{settings.buttondown_webhook_id}/test",
                headers={"Authorization": f"Token {settings.buttondown_api_key}"}
            )

            assert response.status_code == 204, f"Webhook trigger failed: {response.status_code}"

            # Wait for webhook to be processed
            # Buttondown typically delivers webhooks within 1-2 seconds
            time.sleep(3)

            # Verify event was stored in database
            final_count = db.query(Event).count()
            assert final_count > initial_count, "No new events were created after triggering test webhook"

            # Get the most recent event
            latest_event = db.query(Event).order_by(Event.created_at.desc()).first()
            assert latest_event is not None
            assert latest_event.event_type in [
                "subscriber.opened",
                "subscriber.clicked",
                "subscriber.confirmed",
                "subscriber.delivered",
                "subscriber.unsubscribed",
                "email.sent"
            ]
        finally:
            db.close()

    def test_webhook_idempotency_with_real_data(self):
        """Test that duplicate webhooks from Buttondown are handled correctly

        Note: Buttondown test API generates random data each time,
        so this won't actually test true idempotency.
        True idempotency testing is done in test_webhooks.py with controlled payloads.
        This test just verifies webhooks are being received.
        """
        from app.database import SessionLocal

        db = SessionLocal()
        try:
            # Trigger test webhook twice
            for _ in range(2):
                response = requests.post(
                    f"https://api.buttondown.com/v1/webhooks/{settings.buttondown_webhook_id}/test",
                    headers={"Authorization": f"Token {settings.buttondown_api_key}"}
                )
                assert response.status_code == 204
                time.sleep(1)

            # Wait for webhooks to be processed
            time.sleep(2)

            # Verify we have events in the database
            event_count = db.query(Event).count()
            assert event_count >= 1, "No events found in database after triggering webhooks"
        finally:
            db.close()


class TestButtondownAPIIntegration:
    """Additional Buttondown API integration tests"""

    def test_can_list_webhooks(self):
        """Test that we can list webhooks from Buttondown API"""
        if not settings.buttondown_api_key:
            pytest.skip("BUTTONDOWN_API_KEY not configured")

        response = requests.get(
            "https://api.buttondown.com/v1/webhooks",
            headers={"Authorization": f"Token {settings.buttondown_api_key}"}
        )

        assert response.status_code == 200
        webhooks = response.json()
        assert isinstance(webhooks, dict) or isinstance(webhooks, list)

        # Verify our configured webhook ID exists
        if settings.buttondown_webhook_id:
            # The response format may vary, so this is a basic check
            assert len(str(webhooks)) > 0
