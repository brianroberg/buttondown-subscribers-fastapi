# Testing Guide

This guide explains how to validate the Buttondown API ingestion flow in development and production.

## Environment Configuration

Set a Buttondown API key for the environment you are testing:

```bash
# Example (.env.development)
BUTTONDOWN_API_KEY=your-test-newsletter-api-key
BUTTONDOWN_INITIAL_SYNC_LOOKBACK_DAYS=30
```

For production, supply the API key and any overrides through your deployment platform. Never commit API keys to version control.

## Running Tests

All tests are self-contained and do not hit the real Buttondown API.

```bash
# Run unit and service tests
docker compose exec web pytest tests/test_sync.py tests/test_models.py tests/test_main.py -v

# Run the full suite (includes dashboard tests)
docker compose exec web pytest tests/ -v --cov=app --cov-report=html
```

## Manual Verification

1. Start the stack: `docker compose up --build`
2. Trigger a sync:
   ```bash
   curl -X POST http://localhost:8000/api/sync/events
   ```
3. Check sync state:
   ```bash
   curl http://localhost:8000/api/sync/events/state
   ```
4. Inspect the dashboard (`http://localhost:8000/`) to confirm new events appear in charts/tables.

### Verifying Database Changes

```bash
docker compose exec web sqlite3 /app/data/app.db "SELECT event_type, created_at FROM events ORDER BY created_at DESC LIMIT 5;"
docker compose exec web sqlite3 /app/data/app.db "SELECT buttondown_id, email, status FROM subscribers LIMIT 5;"
```

## CI/CD Considerations

- The default test suite does not require Buttondown credentials.
- If you want to run a live ingestion check during CI, provide `BUTTONDOWN_API_KEY` and invoke `curl -X POST /api/sync/events` against a staging deployment.

## Verification Checklist

- [ ] `.env.*` files contain the correct API key for the target environment.
- [ ] `POST /api/sync/events` returns `200` with non-zero `events_created` on the first run.
- [ ] `GET /api/sync/events/state` reports a recent `last_synced_at`.
- [ ] Dashboard stats reflect newly ingested events.
- [ ] Scheduled job (if configured) calls the sync endpoint successfully.

## Troubleshooting

### 401 Unauthorized

- Confirm the API key is valid and scoped to the newsletter you expect.
- Ensure the key was loaded into the running container (`docker compose exec web printenv BUTTONDOWN_API_KEY`).

### No Events Imported

- Check the sync response: `events_skipped` > 0 usually means all events were already ingested.
- If `last_synced_at` is far in the past, pass an explicit lookback window:
  ```bash
  curl -X POST "http://localhost:8000/api/sync/events?since=2025-01-01T00:00:00Z"
  ```
- Review logs for `ButtondownEventSynchronizer` entries (`docker compose logs -f web | grep ButtondownEventSynchronizer`).

### Clock Drift

- The service stores timestamps in UTC. If your environment is not using UTC, ensure any scheduled jobs convert timestamps appropriately when using the `since` parameter.

## Best Practices

1. Use a dedicated Buttondown API key for automated ingestion (read-only scope is sufficient).
2. Configure a scheduler (cron, Cloud Scheduler, GitHub Actions) to call `POST /api/sync/events` regularly.
3. Keep the default lookback window modest (e.g., 30 days) to avoid large initial pulls; adjust via `BUTTONDOWN_INITIAL_SYNC_LOOKBACK_DAYS` if you need a deeper backfill.
4. Monitor sync metrics (`events_created`, `events_skipped`) to detect anomalies early.

## Security Notes

- Store API keys in secrets management (not in source control).
- Rotate keys periodically and revoke unused credentials.
- The service uses HTTPS when deployed behind Cloud Run / reverse proxies—ensure transport security for external calls to the sync endpoint.
