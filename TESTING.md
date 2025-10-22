# Testing Guide

This guide explains how to test the Buttondown webhook integration in development and production environments.

## Environment Configuration

The application supports separate Buttondown configurations for development and production:

### Development Setup (Testing Newsletter)

For development, use a separate Buttondown newsletter with synthetic/test data:

1. Create a testing newsletter in Buttondown (or use an existing test newsletter)
2. Get the API key for your test newsletter
3. Set up the webhook and get its ID
4. Configure in `.env.development`:

```bash
# Development - uses test newsletter with synthetic data
BUTTONDOWN_API_KEY=your-test-newsletter-api-key
BUTTONDOWN_WEBHOOK_ID=your-test-webhook-id
BUTTONDOWN_WEBHOOK_SECRET=your-test-webhook-secret
```

### Production Setup (Real Newsletter)

For production, use your actual newsletter:

1. Configure environment variables for your production container:

```bash
# Production - uses real newsletter
BUTTONDOWN_API_KEY=your-production-api-key
BUTTONDOWN_WEBHOOK_ID=your-production-webhook-id
BUTTONDOWN_WEBHOOK_SECRET=your-production-webhook-secret
```

**Important**: Never commit production API keys to version control!

## Getting Your Webhook ID

### Method 1: Via Buttondown UI
1. Go to Buttondown Settings → Webhooks
2. The webhook ID is in the webhook details or URL

### Method 2: Via API
```bash
curl -H "Authorization: Token YOUR_API_KEY" \
  https://api.buttondown.com/v1/webhooks
```

## Running Tests

### Unit Tests (No API Keys Required)

Run standard unit tests without Buttondown credentials:

```bash
docker compose exec web pytest tests/test_webhooks.py tests/test_models.py tests/test_main.py -v
```

### Integration Tests (Requires API Keys)

Integration tests use Buttondown's testing API and require credentials:

```bash
# Set credentials in .env.development first
docker compose exec web pytest tests/test_webhooks_integration.py -v
```

If credentials aren't configured, integration tests will be automatically skipped:

```
SKIPPED [1] tests/test_webhooks_integration.py: Buttondown API credentials not configured
```

### All Tests

Run complete test suite:

```bash
docker compose exec web pytest tests/ -v --cov=app --cov-report=html
```

## Manual Testing with Buttondown Test API

### Using the Python Utility

```python
from app.utils.buttondown import trigger_test_webhook

# Trigger a test webhook (uses env vars)
trigger_test_webhook()
```

### Using the Shell Scripts

Trigger a test webhook from the command line:

```bash
# Get your webhook ID
/tmp/get_webhooks.sh YOUR_API_KEY

# Trigger test webhook
/tmp/test_webhook.sh YOUR_API_KEY WEBHOOK_ID
```

### Monitor Webhook Processing

Watch logs to see webhooks being processed:

```bash
docker compose logs -f web | grep "Processed"
```

## Testing Workflow

### Development Workflow

1. **Setup**: Configure test newsletter credentials in `.env.development`
2. **Develop**: Make changes to webhook processing code
3. **Unit Test**: Run `pytest tests/test_webhooks.py` (fast, no API calls)
4. **Integration Test**: Run `pytest tests/test_webhooks_integration.py` (triggers real webhooks)
5. **Manual Test**: Use test scripts or Python utility to trigger webhooks
6. **Verify**: Check logs and database for processed events

### CI/CD Testing

For CI/CD pipelines:

```bash
# Run tests without integration tests (no API keys needed)
pytest tests/ -v -m "not integration"

# Or run all tests with credentials from secrets
export BUTTONDOWN_API_KEY=${{ secrets.BUTTONDOWN_TEST_API_KEY }}
export BUTTONDOWN_WEBHOOK_ID=${{ secrets.BUTTONDOWN_TEST_WEBHOOK_ID }}
pytest tests/ -v
```

## Verification Checklist

After setting up testing:

- [ ] `.env.development` has test newsletter credentials
- [ ] Integration tests can trigger webhooks: `pytest tests/test_webhooks_integration.py -v`
- [ ] Manual test webhook works: `/tmp/test_webhook.sh API_KEY WEBHOOK_ID`
- [ ] Logs show webhook processing: `docker compose logs -f web | grep "Processed"`
- [ ] Events stored in database correctly
- [ ] Production credentials are configured via environment (not in files)

## Troubleshooting

### Integration Tests Skipped

**Problem**: Tests show "Buttondown API credentials not configured"

**Solution**: Set `BUTTONDOWN_API_KEY` and `BUTTONDOWN_WEBHOOK_ID` in `.env.development`

### 401 Unauthorized

**Problem**: API returns 401 when triggering test webhook

**Solution**: Verify your API key is correct and has webhook access

### 404 Not Found

**Problem**: API returns 404 for webhook ID

**Solution**: Verify webhook ID is correct using `/tmp/get_webhooks.sh`

### No Events in Database

**Problem**: Test webhook triggered but no events appear

**Solution**:
1. Check logs: `docker compose logs web | tail -50`
2. Verify webhook URL in Buttondown points to your endpoint
3. Ensure port 8000 is public (for Codespaces)
4. Check for errors in webhook processing

## Best Practices

1. **Always use test newsletter for development** - Never test with production data
2. **Keep production keys in environment** - Use secrets management in production
3. **Run integration tests before deploying** - Verify webhook processing works
4. **Monitor webhook failures** - Check logs regularly for errors
5. **Use test API for automated testing** - Don't rely on manual clicking

## Security Notes

- **API Keys**: Never commit API keys to version control
- **Webhook Secrets**: Store securely and rotate periodically
- **Test Data**: Use synthetic data that doesn't expose real subscriber information
- **Separate Environments**: Use different newsletters for dev/staging/production
