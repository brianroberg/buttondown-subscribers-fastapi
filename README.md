# Buttondown Subscriber Engagement Tracker

A self-hosted web application that integrates with the Buttondown newsletter API to track and analyze subscriber engagement metrics, focusing on email opens and click-through rates to identify the most active subscribers.

## Tech Stack

- **Backend**: FastAPI (Python 3.12)
- **Database**: SQLite with Cloud Storage FUSE (Cloud Run deployment)
- **Frontend**: Vue.js 3 (planned - Phase 5)
- **Containerization**: Docker with multi-stage builds
- **Deployment**: Google Cloud Run
- **Testing**: pytest with 87% code coverage

## Features

- ✅ Real-time webhook receiver for Buttondown events
- ✅ SQLite database with optimized indexes
- ✅ Event processing with idempotency
- ✅ Comprehensive test suite (38 tests, 87% coverage)
- 🚧 Analytics API endpoints (Phase 4)
- 🚧 Vue.js dashboard (Phase 5)
- 🚧 Cloud Run deployment (Phase 6)

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Buttondown account with API access

### Initial Setup

1. **Clone and configure environment**:
   ```bash
   cp .env.example .env.development
   # Edit .env.development with your Buttondown credentials
   ```

2. **Build and start the development environment**:
   ```bash
   docker compose up -d
   ```

3. **Verify the application is running**:
   ```bash
   curl http://localhost:8000/health
   # Should return: {"status":"healthy"}
   ```

4. **Access the API documentation**:
   - OpenAPI docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Development Workflow

### Running the Application

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f web

# Stop all services
docker compose down
```

### Making Code Changes

The application supports hot-reload in development mode:
- Edit files in `app/` directory
- Changes are automatically detected and the server restarts
- No need to rebuild the container for code changes

### When to Rebuild the Container

Rebuild the container when you make changes to:
- `requirements.txt` or `requirements-dev.txt`
- `Dockerfile.dev`
- `docker-compose.yml`

```bash
docker compose build web
docker compose up -d
```

## Testing

### Running Tests

There are two ways to run tests, each with different use cases:

#### Option 1: `docker compose exec` (Recommended for Development)

Use this when running tests repeatedly during development:

```bash
# Run all tests
docker compose exec web pytest

# Run with verbose output
docker compose exec web pytest -v

# Run specific test file
docker compose exec web pytest tests/test_webhooks.py

# Run specific test
docker compose exec web pytest tests/test_webhooks.py::test_webhook_health

# Run with coverage report
docker compose exec web pytest --cov-report=term-missing
```

**When to use `exec`:**
- ✅ Fast repeated test runs during development
- ✅ Container is already running
- ✅ No configuration changes since container started
- ❌ Don't use after modifying `pytest.ini`, `requirements-dev.txt`, or Docker config

#### Option 2: `docker compose run --rm` (Fresh Environment)

Use this when you need a clean test environment:

```bash
# Run all tests in fresh container
docker compose run --rm web pytest

# Run with verbose output
docker compose run --rm web pytest -v

# Run specific test file
docker compose run --rm web pytest tests/test_webhooks.py
```

**When to use `run --rm`:**
- ✅ After changing `pytest.ini` configuration
- ✅ After updating dependencies in `requirements-dev.txt`
- ✅ After modifying Docker configuration
- ✅ When you want to ensure tests run in a clean environment
- ✅ In CI/CD pipelines
- ❌ Slower than `exec` (creates new container each time)

**The key difference:**
- `exec` runs tests in the **existing running container**
- `run --rm` creates a **fresh container** with current configuration, runs tests, then removes it

### Test Coverage

Current coverage: **87%** (target: 80%)

```bash
# Run tests with detailed coverage report
docker compose exec web pytest --cov=app --cov-report=term-missing

# Generate HTML coverage report (inside container)
docker compose exec web pytest --cov=app --cov-report=html
# Report saved to htmlcov/ inside container
```

### Running Specific Test Suites

```bash
# Unit tests only
docker compose exec web pytest tests/test_models.py tests/test_schemas.py

# Webhook tests
docker compose exec web pytest tests/test_webhooks.py

# Integration tests (requires Buttondown credentials)
docker compose exec web pytest tests/test_webhooks_integration.py

# Skip integration tests
docker compose exec web pytest -m "not integration"
```

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic settings management
│   ├── database.py          # SQLAlchemy database setup
│   ├── models.py            # Database ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   └── webhooks.py      # Webhook endpoints
│   └── utils/
│       ├── __init__.py
│       ├── logging.py       # Structured logging
│       └── buttondown.py    # Buttondown API utilities
├── data/                    # SQLite database (gitignored)
├── tests/
│   ├── conftest.py          # pytest fixtures
│   ├── test_main.py         # Application tests
│   ├── test_models.py       # Database model tests
│   ├── test_schemas.py      # Schema validation tests
│   ├── test_webhooks.py     # Webhook endpoint tests
│   └── test_webhooks_integration.py  # Buttondown API integration tests
├── docker-compose.yml       # Development environment
├── Dockerfile.dev           # Development container
├── Dockerfile               # Production container (Cloud Run)
├── pytest.ini               # pytest configuration
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── README.md
```

## Configuration

### Environment Variables

Key environment variables (set in `.env.development`):

```bash
# Application
ENVIRONMENT=development
DEBUG=true
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/dev.db
DB_PATH=./data/dev.db

# Buttondown Integration
BUTTONDOWN_WEBHOOK_SECRET=your-webhook-secret
BUTTONDOWN_API_KEY=your-api-key
BUTTONDOWN_WEBHOOK_ID=your-webhook-id

# Security
SECRET_KEY=your-secret-key
LOG_LEVEL=DEBUG
```

### Database Configuration

The application uses SQLite with the following optimizations:
- WAL (Write-Ahead Logging) mode for better concurrency
- 64MB cache size
- 5-second busy timeout
- Foreign key constraints enabled

## Webhook Setup

1. **Configure webhook in Buttondown**:
   - Navigate to Buttondown Settings → Webhooks
   - Add webhook URL: `http://your-domain/webhooks/buttondown`
   - Select events: `subscriber.opened`, `subscriber.clicked`, `subscriber.confirmed`, `subscriber.delivered`, `subscriber.unsubscribed`, `email.sent`
   - Copy webhook secret to `.env.development`

2. **Test webhook locally** (using ngrok or similar):
   ```bash
   # Start ngrok
   ngrok http 8000
   
   # Update Buttondown webhook URL with ngrok URL
   # Test webhook delivery from Buttondown dashboard
   ```

3. **View webhook logs**:
   ```bash
   docker compose logs -f web | grep webhook
   ```

## Database Management

### Access SQLite database:

```bash
# Enter container
docker compose exec web bash

# Open database
sqlite3 /app/data/dev.db

# Useful queries
.tables                           # List all tables
.schema subscribers               # Show table schema
SELECT * FROM subscribers LIMIT 5;
SELECT * FROM events ORDER BY created_at DESC LIMIT 10;
```

### Reset database:

```bash
# Stop container
docker compose down

# Remove database file
rm -rf data/

# Restart (database will be recreated)
docker compose up -d
```

## Code Quality

### Linting

```bash
# Check code with Ruff
docker compose exec web ruff check app/

# Auto-fix issues
docker compose exec web ruff check app/ --fix

# Format code with Black
docker compose exec web black app/
```

### Type Checking

```bash
# Run mypy type checker
docker compose exec web mypy app/
```

## Deployment

### Production Build

```bash
# Build production image
docker build -t buttondown-tracker -f Dockerfile .

# Test production image locally
docker run -p 8080:8080 \
  -e DATABASE_URL=sqlite:///./data/app.db \
  -e SECRET_KEY=production-secret \
  -v $(pwd)/data:/app/data \
  buttondown-tracker
```

### Cloud Run Deployment

See deployment guide in `thoughts/shared/plans/2025-10-22-buttondown-engagement-tracker.md` Phase 6.

```bash
# Deploy to Cloud Run
gcloud run deploy buttondown-tracker \
  --image gcr.io/PROJECT_ID/buttondown-tracker:latest \
  --region us-central1 \
  --platform managed \
  --min-instances 1 \
  --max-instances 1
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs web

# Rebuild from scratch
docker compose down
docker compose build --no-cache web
docker compose up -d
```

### Tests failing after config changes

```bash
# Restart container to load new configuration
docker compose restart web

# Or use run --rm for fresh environment
docker compose run --rm web pytest
```

### Database locked errors

SQLite has limited concurrency. Ensure:
- Only one instance is running (`max-instances=1` on Cloud Run)
- Database file is not being accessed by multiple processes

### Hot reload not working

```bash
# Check if volume mount is correct in docker-compose.yml
docker compose config

# Verify files are mounted
docker compose exec web ls -la /app/app
```

## Contributing

1. Create tests for new features
2. Ensure test coverage stays above 80%
3. Run linting before committing: `ruff check app/ --fix`
4. All tests must pass: `docker compose run --rm web pytest`

## License

[Your License Here]

## Support

For issues or questions, please open an issue on GitHub.
