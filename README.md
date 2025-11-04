# Buttondown Subscriber Engagement Tracker

Track Buttondown newsletter engagement events (opens, clicks, confirmations) and expose them through a FastAPI service plus optional dashboard frontend.

## Development Setup

1. Install Docker and Docker Compose.
2. Clone the repo and copy the sample env:
   ```bash
   git clone https://github.com/your-org/buttondown-subscribers-fastapi.git
   cd buttondown-subscribers-fastapi
   cp .env.example .env.development
   ```
3. Fill in `.env.development` with demo/testing credentials. Development defaults hit the Buttondown demo API and the “Moogle Reader Updates” newsletter.
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
6. Visit `http://localhost:8000/` for the dashboard (served from the built assets) or `http://localhost:8000/docs` for the OpenAPI UI.

## Production Setup

1. Provide real Buttondown credentials and set `BUTTONDOWN_NEWSLETTER_NAME="Brian & Carin Roberg's Ministry Updates"` along with a strong `SECRET_KEY`.
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
     --set-env-vars SECRET_KEY=replace-me
   ```
