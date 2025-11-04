# Buttondown Subscriber Engagement Tracker

Track Buttondown newsletter engagement events (opens, clicks, confirmations) by polling the Buttondown REST API and expose them through a FastAPI service plus optional dashboard frontend. The application remembers the watermark of the last successful sync so each run only ingests new activity.

## Development Setup

1. Install Docker and Docker Compose.
2. Clone the repo and copy the sample env:
   ```bash
   git clone https://github.com/your-org/buttondown-subscribers-fastapi.git
   cd buttondown-subscribers-fastapi
   cp .env.example .env.development
   ```
3. Fill in `.env.development` with demo/testing credentials. At minimum you need `BUTTONDOWN_API_KEY` (scoped to read events) and optionally override `BUTTONDOWN_INITIAL_SYNC_LOOKBACK_DAYS` to control the first sync window.
4. Build the frontend once so FastAPI can serve the dashboard:
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
   If the stack was already running, run `docker compose restart web` afterward so Uvicorn picks up the new build. For live frontend development, run `npm run dev -- --host` instead and work from `http://localhost:3000`.
5. Start the backend stack:
   ```bash
   docker compose up --build
   ```
   Docker automatically provisions a named volume called `data` for the SQLite database.
6. Visit `http://localhost:8000/` for the dashboard (served from the built assets) or `http://localhost:8000/docs` for the OpenAPI UI. Kick off an initial ingest with:
   ```bash
   curl -X POST http://localhost:8000/api/sync/events
   ```
   Subsequent runs only fetch events created after the previous ingest.

## Production Setup

1. Provide real Buttondown credentials and set `BUTTONDOWN_NEWSLETTER_NAME="Brian & Carin Roberg's Ministry Updates"` along with a strong `SECRET_KEY`. Set `BUTTONDOWN_API_KEY` to a production API token and (optionally) customise `BUTTONDOWN_INITIAL_SYNC_LOOKBACK_DAYS`.
2. Build the production image:
   ```bash
   docker build -t buttondown-tracker .
   ```
3. Push the image to your registry:
   ```bash
   docker tag buttondown-tracker gcr.io/PROJECT_ID/buttondown-tracker:latest
   docker push gcr.io/PROJECT_ID/buttondown-tracker:latest
   ```
4. Deploy the image to your platform (e.g., Cloud Run), supplying environment variables and secrets there. Ensure `/app/data` is backed by persistent storage (Cloud Run users typically mount Cloud Storage FUSE or connect to Cloud SQL instead of SQLite). For Cloud Run:
   ```bash
   gcloud run deploy buttondown-tracker \
     --image gcr.io/PROJECT_ID/buttondown-tracker:latest \
     --region us-central1 \
     --set-env-vars ENVIRONMENT=production,BUTTONDOWN_API_BASE_URL=https://api.buttondown.com/v1 \
     --set-env-vars BUTTONDOWN_NEWSLETTER_NAME="Brian & Carin Roberg's Ministry Updates" \
     --set-env-vars BUTTONDOWN_API_KEY=replace-me \
     --set-env-vars SECRET_KEY=replace-me
   ```

## Synchronising Buttondown data

- `POST /api/sync/events`: Fetches engagement events from Buttondown, stores new subscribers/events, and advances an internal watermark (`sync_states.buttondown_events.last_synced_at`). Optional `since` query parameter forces a lookback window (ISO 8601 timestamp).
- `GET /api/sync/events/state`: Returns the current watermark and the configured default lookback window. Useful for health checks or scheduling jobs.

Recommended workflow:

1. Run the sync endpoint on a schedule (e.g., Cloud Scheduler, GitHub Actions, cron) to keep the dashboard fresh.
2. Use the `default_lookback_days` setting for the initial backfill. Afterwards, incremental runs are bounded by the stored `last_synced_at`.
3. Monitor logs for `ButtondownEventSynchronizer` entries, which include counts of ingested events and subscribers.
