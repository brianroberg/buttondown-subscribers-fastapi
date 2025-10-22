"""Buttondown API utilities for testing and integration"""

import requests
import logging
from typing import Optional, Dict, Any
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ButtondownAPIError(Exception):
    """Raised when Buttondown API returns an error"""
    pass


class ButtondownAPI:
    """Client for Buttondown API interactions"""

    BASE_URL = "https://api.buttondown.com/v1"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Buttondown API client

        Args:
            api_key: Buttondown API key. If not provided, uses BUTTONDOWN_API_KEY from settings
        """
        self.api_key = api_key or settings.buttondown_api_key
        if not self.api_key:
            raise ValueError("Buttondown API key not configured")

        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    def trigger_test_webhook(self, webhook_id: Optional[str] = None) -> bool:
        """
        Trigger a test webhook from Buttondown

        This sends a webhook with fake/test data to your configured webhook endpoint.
        Useful for testing webhook processing without real subscriber events.

        Args:
            webhook_id: Webhook ID to test. If not provided, uses BUTTONDOWN_WEBHOOK_ID from settings

        Returns:
            True if test webhook was triggered successfully

        Raises:
            ButtondownAPIError: If the API request fails
        """
        webhook_id = webhook_id or settings.buttondown_webhook_id
        if not webhook_id:
            raise ValueError("Webhook ID not configured")

        url = f"{self.BASE_URL}/webhooks/{webhook_id}/test"

        try:
            response = requests.post(url, headers=self.headers, timeout=10)

            if response.status_code == 204:
                logger.info(f"Successfully triggered test webhook for ID: {webhook_id}")
                return True
            else:
                error_msg = f"Failed to trigger test webhook: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise ButtondownAPIError(error_msg)

        except requests.RequestException as e:
            raise ButtondownAPIError(f"Request failed: {str(e)}")

    def list_webhooks(self) -> Dict[str, Any]:
        """
        List all webhooks configured in Buttondown

        Returns:
            Dictionary containing webhook information

        Raises:
            ButtondownAPIError: If the API request fails
        """
        url = f"{self.BASE_URL}/webhooks"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to list webhooks: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise ButtondownAPIError(error_msg)

        except requests.RequestException as e:
            raise ButtondownAPIError(f"Request failed: {str(e)}")

    def get_webhook(self, webhook_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get details for a specific webhook

        Args:
            webhook_id: Webhook ID. If not provided, uses BUTTONDOWN_WEBHOOK_ID from settings

        Returns:
            Dictionary containing webhook details

        Raises:
            ButtondownAPIError: If the API request fails
        """
        webhook_id = webhook_id or settings.buttondown_webhook_id
        if not webhook_id:
            raise ValueError("Webhook ID not configured")

        url = f"{self.BASE_URL}/webhooks/{webhook_id}"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                error_msg = f"Failed to get webhook: HTTP {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise ButtondownAPIError(error_msg)

        except requests.RequestException as e:
            raise ButtondownAPIError(f"Request failed: {str(e)}")


def trigger_test_webhook(webhook_id: Optional[str] = None, api_key: Optional[str] = None) -> bool:
    """
    Convenience function to trigger a test webhook

    Args:
        webhook_id: Webhook ID to test
        api_key: Buttondown API key

    Returns:
        True if successful

    Example:
        >>> from app.utils.buttondown import trigger_test_webhook
        >>> trigger_test_webhook()  # Uses env vars
        True
    """
    client = ButtondownAPI(api_key=api_key)
    return client.trigger_test_webhook(webhook_id=webhook_id)
