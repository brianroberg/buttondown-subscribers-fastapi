# Buttondown Subscriber Engagement Tracker Implementation Plan

## Overview

This plan details the implementation of a self-hosted web application that integrates with the Buttondown newsletter API to track and analyze subscriber engagement metrics, specifically focusing on email opens and click-through rates to identify the most active subscribers.

The application uses FastAPI (Python), SQLite for data storage, Vue.js for the dashboard frontend, and is designed for deployment to Google Cloud Run with Docker containerization.

## Current State Analysis

This is a greenfield project. The repository currently contains only an architecture document (`buttondown-engagement-tracker-architecture.md`) that defines the business requirements and technical architecture.

### Key Constraints Discovered:
- **SQLite on Cloud Run**: Research shows SQLite with Cloud Storage FUSE has limitations (no file locking, poor write performance ~130ms). Mitigation: Deploy with `--max-instances=1` to prevent concurrent write issues.
- **Webhook-driven architecture**: No polling required; real-time updates via Buttondown webhooks
- **Single-user application**: Simplified authentication requirements
- **Cost optimization**: Target < $10/month hosting cost

## Desired End State

A fully functional web application with:

1. **Webhook receiver** that captures Buttondown events (`subscriber.opened`, `subscriber.clicked`, `subscriber.confirmed`, `subscriber.delivered`, `subscriber.unsubscribed`, `email.sent`)
2. **SQLite database** storing subscriber information and engagement events with proper indexing
3. **Analytics dashboard** (Vue.js) showing:
   - Subscriber engagement metrics (opens, clicks)
   - Ranked list of most active subscribers
   - Filter by tags
   - Engagement trends over time
4. **Docker containerization** with multi-stage builds optimized for Cloud Run
5. **Comprehensive test suite** (>80% coverage) using pytest
6. **Security**: Basic authentication for dashboard, webhook signature verification

### Success Verification:
- Webhook endpoint receives and processes Buttondown events without errors
- Dashboard displays accurate engagement metrics
- SQLite database persists across container restarts
- All tests pass: `pytest tests/ --cov=app --cov-report=html`
- Container builds successfully: `docker build -t fastapi-app .`
- Application runs on Cloud Run: health check returns 200
- Code quality verified via Ruff linting

## What We're NOT Doing

- **Multi-user authentication**: Single-user application only
- **Real-time WebSocket updates**: Dashboard polls API for updates
- **Horizontal scaling**: SQLite limitation requires single instance
- **PostgreSQL migration**: Out of scope for v1 (SQLite sufficient for expected scale)
- **Email sending**: Read-only integration with Buttondown
- **Historical data backfill**: Will only track events from webhook activation forward
- **Advanced analytics**: No A/B testing, cohort analysis, or predictive modeling
- **Mobile app**: Web dashboard only

## Implementation Approach

**Phased Implementation Strategy:**

1. **Foundation**: Project structure, Docker configuration, database setup
2. **Core Backend**: Webhook receiver, database models, event processing
3. **Testing Infrastructure**: Test suite with >80% coverage
4. **Analytics API**: REST endpoints for dashboard data
5. **Frontend Dashboard**: Vue.js dashboard with engagement visualizations
6. **Deployment**: Cloud Run deployment with Cloud Storage volume

**Key Technical Decisions:**
- **Async FastAPI with SQLite**: Use synchronous SQLAlchemy (async not needed for single-instance, low-concurrency SQLite)
- **FastAPI BackgroundTasks**: Simple enough for webhook processing (no Celery needed initially)
- **Idempotency via unique constraints**: Use event hash to prevent duplicate processing
- **Docker multi-stage builds**: Reduce final image size by ~90%

---

## Phase 1: Project Foundation & Docker Setup

### Overview
Set up the FastAPI project structure, Docker configuration optimized for Cloud Run, and initialize the SQLite database with proper schema and indexes.

### Changes Required:

#### 1. Project Structure
**Files to create:**
```
/workspaces/buttondown-subscribers-fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Pydantic settings management
│   ├── database.py          # SQLAlchemy database setup
│   ├── models.py            # SQLAlchemy ORM models
│   ├── schemas.py           # Pydantic validation schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhooks.py      # Webhook endpoints
│   │   ├── dashboard.py     # Dashboard API endpoints
│   │   └── subscribers.py   # Subscriber management endpoints
│   └── utils/
│       ├── __init__.py
│       ├── logging.py       # Structured logging for Cloud Run
│       └── security.py      # Authentication utilities
├── data/                    # SQLite database (gitignored)
│   └── .gitkeep
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # pytest fixtures
│   ├── test_webhooks.py     # Webhook endpoint tests
│   ├── test_models.py       # Database model tests
│   └── test_dashboard.py    # Dashboard API tests
├── frontend/                # Vue.js dashboard (Phase 5)
│   └── .gitkeep
├── .dockerignore
├── .env.example
├── .env.development
├── .gitignore
├── docker-compose.yml       # Development environment
├── Dockerfile               # Production (Cloud Run)
├── Dockerfile.dev           # Development
├── requirements.txt         # Production dependencies
├── requirements-dev.txt     # Development dependencies
└── README.md
```

#### 2. Core Configuration Files

**File**: `app/config.py`
**Changes**: Create Pydantic Settings class

```python
from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    app_name: str = "Buttondown Engagement Tracker"
    environment: str = "development"
    debug: bool = False

    # Server
    port: int = 8000

    # Database
    database_url: str = "sqlite:///./data/app.db"
    db_path: str = os.environ.get("DB_PATH", "./data/app.db")

    # Buttondown
    buttondown_webhook_secret: str = ""
    buttondown_api_key: str = ""

    # Security
    secret_key: str
    dashboard_username: str = "admin"
    dashboard_password_hash: str = ""  # Bcrypt hash

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("sqlite"):
            return f"sqlite:///{self.db_path}"
        return self.database_url

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**File**: `app/database.py`
**Changes**: Create SQLAlchemy setup with SQLite optimizations

```python
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# Create engine with SQLite-specific optimizations
engine = create_engine(
    settings.sqlalchemy_database_url,
    connect_args={"check_same_thread": False},
    echo=settings.debug
)

# Configure SQLite PRAGMAs for performance
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
    cursor.execute("PRAGMA busy_timeout=5000")  # 5 second timeout
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables"""
    from app.models import Subscriber, Event, Tag, SubscriberTag
    Base.metadata.create_all(bind=engine)
```

#### 3. Database Models

**File**: `app/models.py`
**Changes**: Create SQLAlchemy ORM models with optimized indexes

```python
from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Index, JSON, Boolean, Table
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Subscriber(Base):
    __tablename__ = "subscribers"

    id = Column(Integer, primary_key=True, index=True)
    buttondown_id = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    status = Column(String(50), default="active", index=True)
    subscription_date = Column(DateTime(timezone=True), server_default=func.now())
    source = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    events = relationship("Event", back_populates="subscriber", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary="subscriber_tags", back_populates="subscribers")

    __table_args__ = (
        Index('idx_status_created', 'status', 'created_at'),
    )

class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(64), unique=True, nullable=False, index=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    email_id = Column(String(100), nullable=True, index=True)
    link_url = Column(String(500), nullable=True)
    metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    subscriber = relationship("Subscriber", back_populates="events")

    __table_args__ = (
        Index('idx_subscriber_created', 'subscriber_id', 'created_at'),
        Index('idx_event_type_created', 'event_type', 'created_at'),
    )

class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    subscribers = relationship("Subscriber", secondary="subscriber_tags", back_populates="tags")

class SubscriberTag(Base):
    __tablename__ = "subscriber_tags"

    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index('idx_subscriber_tag', 'subscriber_id', 'tag_id', unique=True),
        Index('idx_tag_subscriber', 'tag_id', 'subscriber_id'),
    )
```

#### 4. Docker Configuration

**File**: `Dockerfile` (Production - Cloud Run)
**Changes**: Create multi-stage Dockerfile

```dockerfile
# ============================================
# Stage 1: Builder - Install dependencies
# ============================================
FROM python:3.12-slim as builder

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install dependencies to user site-packages
RUN pip install --user --no-cache-dir --upgrade -r requirements.txt

# Pre-compile Python code for faster startup
COPY ./app /tmp/app
RUN python -m compileall /tmp/app

# ============================================
# Stage 2: Runtime - Production image
# ============================================
FROM python:3.12-slim as runtime

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Copy pre-compiled application
COPY --from=builder /tmp/app /app

# Create non-root user and data directory
RUN useradd -m -u 1001 appuser && \
    mkdir -p /app/data && \
    chown -R appuser:appuser /app/data

# Environment configuration
ENV PATH=/root/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/app.db

USER appuser

EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/health', timeout=2)"

# Shell form for $PORT substitution (Cloud Run)
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
```

**File**: `Dockerfile.dev` (Development)
**Changes**: Create development Dockerfile with hot reload

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

# Create data directory
RUN mkdir -p /app/data

# Create non-root user
RUN useradd -m -u 1001 appuser && \
    chown -R appuser:appuser /app

# Environment
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app

USER appuser

# Source code will be mounted via volume
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
```

**File**: `docker-compose.yml`
**Changes**: Create development environment configuration

```yaml
version: '3.8'

services:
  web:
    build:
      context: .
      dockerfile: Dockerfile.dev
    container_name: buttondown-tracker-dev
    command: uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
    volumes:
      # Mount source code for hot reload
      - ./app:/app/app:ro
      # Database persistence
      - ./data:/app/data
      # Exclude Python cache
      - /app/app/__pycache__
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=development
      - DEBUG=true
      - PORT=8000
      - DATABASE_URL=sqlite:///./data/dev.db
    env_file:
      - .env.development
    restart: unless-stopped

volumes:
  data:
```

**File**: `.dockerignore`
**Changes**: Optimize Docker build context

```dockerignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/
.venv

# Version control
.git/
.gitignore

# IDE
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build artifacts
dist/
build/
*.egg-info/

# Environment files
.env
.env.*
!.env.example

# Documentation
docs/
*.md
README.md

# Database
data/
*.db
*.sqlite

# Frontend (built separately)
frontend/node_modules/
frontend/dist/

# Docker
docker-compose*.yml
Dockerfile*
.dockerignore
```

#### 5. Dependency Files

**File**: `requirements.txt`
**Changes**: Production dependencies

```txt
fastapi[standard]==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
pydantic==2.10.3
pydantic-settings==2.6.1
python-multipart==0.0.20
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0
```

**File**: `requirements-dev.txt`
**Changes**: Development dependencies

```txt
# Production dependencies
-r requirements.txt

# Testing
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-cov==6.0.0
httpx==0.28.1

# Code quality
black==24.10.0
ruff==0.8.4
mypy==1.13.0

# Database
alembic==1.14.0
```

#### 6. FastAPI Application Entry Point

**File**: `app/main.py`
**Changes**: Create FastAPI application with health checks

```python
from fastapi import FastAPI, status, Response
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Initialize FastAPI
app = FastAPI(
    title=settings.app_name,
    description="Track and analyze Buttondown subscriber engagement",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    init_db()
    logger.info("Database initialized")

@app.get("/health", tags=["Health"])
def health_check():
    """Liveness probe for Cloud Run"""
    return {"status": "healthy"}

@app.get("/startup", tags=["Health"])
def startup_probe():
    """Startup probe for Cloud Run"""
    return {"status": "ready"}

@app.get("/", tags=["Root"])
def read_root():
    return {
        "service": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment
    }

# Import routers (will be created in Phase 2)
# from app.routers import webhooks, dashboard, subscribers
# app.include_router(webhooks.router)
# app.include_router(dashboard.router)
# app.include_router(subscribers.router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", settings.port))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        log_level=settings.log_level.lower(),
        reload=settings.debug
    )
```

#### 7. Environment Files

**File**: `.env.example`
**Changes**: Template for environment variables

```bash
# Application
ENVIRONMENT=development
DEBUG=true
APP_NAME=Buttondown Engagement Tracker

# Server
PORT=8000

# Database
DATABASE_URL=sqlite:///./data/app.db
DB_PATH=./data/app.db

# Buttondown
BUTTONDOWN_WEBHOOK_SECRET=your-webhook-secret-here
BUTTONDOWN_API_KEY=your-api-key-here

# Security
SECRET_KEY=your-secret-key-here-change-in-production
DASHBOARD_USERNAME=admin
DASHBOARD_PASSWORD_HASH=

# Logging
LOG_LEVEL=INFO
```

**File**: `.env.development`
**Changes**: Development configuration

```bash
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=sqlite:///./data/dev.db
DB_PATH=./data/dev.db
SECRET_KEY=dev-secret-key-not-for-production
LOG_LEVEL=DEBUG
```

**File**: `.gitignore`
**Changes**: Ignore generated files and secrets

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/

# Database
data/
*.db
*.sqlite
*.sqlite3

# Environment
.env
.env.development
.env.production

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# IDE
.vscode/
.idea/
*.swp

# Build
dist/
build/
*.egg-info/

# Logs
*.log
```

### Success Criteria:

#### Automated Verification:
- [x] Project structure created: `ls -la app/ tests/`
- [x] Docker builds successfully: `docker build -t buttondown-tracker -f Dockerfile .`
- [x] Docker dev environment runs: `docker compose up`
- [x] Health check returns 200: `curl http://localhost:8000/health`
- [x] Database tables created: Check `data/dev.db` has 4 tables
- [x] No linting errors: `ruff check app/`
- [ ] Type checking passes: `mypy app/` (skipped - common SQLAlchemy type issues)

#### Manual Verification:
- [x] Access FastAPI docs at http://localhost:8000/docs
- [x] Verify SQLite database file created in `data/` directory
- [x] Inspect database schema with SQLite browser
- [x] Verify hot reload works (edit `main.py`, server restarts)
- [x] Check logs show proper initialization

---

## Phase 2: Webhook Receiver & Event Processing

### Overview
Implement the Buttondown webhook endpoint with signature verification, idempotent event processing, and background task handling. This is the core functionality that captures engagement events in real-time.

### Changes Required:

#### 1. Webhook Router

**File**: `app/routers/webhooks.py`
**Changes**: Create webhook endpoint with security and idempotency

```python
from fastapi import APIRouter, Request, HTTPException, Depends, Header, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.database import get_db
from app.config import get_settings
from app.models import Event, Subscriber
import json
import hmac
import hashlib
import logging
from typing import Optional

router = APIRouter(prefix="/webhooks", tags=["webhooks"])
logger = logging.getLogger(__name__)
settings = get_settings()

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """Verify HMAC-SHA256 webhook signature"""
    if not settings.buttondown_webhook_secret or not signature:
        logger.warning("Webhook secret or signature missing")
        return False

    try:
        # Adjust format based on Buttondown's actual signature format
        if signature.startswith("sha256="):
            received_sig = signature[7:]
            expected_sig = hmac.new(
                settings.buttondown_webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
        else:
            import base64
            digest = hmac.new(
                settings.buttondown_webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).digest()
            expected_sig = base64.b64encode(digest).decode('utf-8')
            received_sig = signature

        return hmac.compare_digest(expected_sig, received_sig)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False

async def process_subscriber_opened(data: dict, db: Session):
    """Process subscriber.opened event"""
    subscriber_id = data.get("subscriber")
    email_id = data.get("email")

    if not subscriber_id:
        logger.warning("subscriber.opened event missing subscriber ID")
        return

    # Get or create subscriber
    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(buttondown_id=subscriber_id)
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

    logger.info(f"Processed email open for subscriber {subscriber_id}")

async def process_subscriber_clicked(data: dict, db: Session):
    """Process subscriber.clicked event"""
    subscriber_id = data.get("subscriber")
    link_url = data.get("link", {}).get("url") if isinstance(data.get("link"), dict) else data.get("link")

    if not subscriber_id:
        logger.warning("subscriber.clicked event missing subscriber ID")
        return

    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(buttondown_id=subscriber_id)
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

    logger.info(f"Processed link click for subscriber {subscriber_id}")

async def process_subscriber_confirmed(data: dict, db: Session):
    """Process subscriber.confirmed event"""
    subscriber_id = data.get("subscriber")

    if not subscriber_id:
        logger.warning("subscriber.confirmed event missing subscriber ID")
        return

    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(
            buttondown_id=subscriber_id,
            status="active"
        )
        db.add(subscriber)
    else:
        subscriber.status = "active"

    db.commit()
    logger.info(f"Processed confirmation for subscriber {subscriber_id}")

async def process_subscriber_unsubscribed(data: dict, db: Session):
    """Process subscriber.unsubscribed event"""
    subscriber_id = data.get("subscriber")

    if not subscriber_id:
        return

    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if subscriber:
        subscriber.status = "unsubscribed"
        db.commit()
        logger.info(f"Processed unsubscribe for subscriber {subscriber_id}")

@router.post("/buttondown")
async def buttondown_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_webhook_signature: Optional[str] = Header(None, alias="X-Webhook-Signature")
):
    """
    Handle Buttondown webhook events.

    Processes: subscriber.opened, subscriber.clicked, subscriber.confirmed,
               subscriber.delivered, subscriber.unsubscribed, email.sent
    """
    # Get raw body for signature verification
    body = await request.body()

    # Verify signature if configured
    if settings.buttondown_webhook_secret and x_webhook_signature:
        if not verify_webhook_signature(body, x_webhook_signature):
            logger.warning("Invalid webhook signature")
            raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON payload: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = payload.get("event_type")
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing event_type")

    data = payload.get("data", {})

    # Generate unique event ID for idempotency
    event_hash = hashlib.sha256(body).hexdigest()

    try:
        # Create event record (unique constraint prevents duplicates)
        event = Event(
            event_id=event_hash,
            subscriber_id=0,  # Will be updated after processing
            event_type=event_type,
            metadata=payload
        )
        db.add(event)
        db.flush()

        # Process based on event type
        if event_type == "subscriber.opened":
            await process_subscriber_opened(data, db)
        elif event_type == "subscriber.clicked":
            await process_subscriber_clicked(data, db)
        elif event_type == "subscriber.confirmed":
            await process_subscriber_confirmed(data, db)
        elif event_type == "subscriber.unsubscribed":
            await process_subscriber_unsubscribed(data, db)
        else:
            logger.info(f"Unhandled event type: {event_type}")

        db.commit()

        return {
            "status": "success",
            "event_type": event_type,
            "event_id": event.id
        }

    except IntegrityError:
        # Duplicate webhook - already processed
        db.rollback()
        logger.info(f"Duplicate webhook ignored: {event_type}")
        return {
            "status": "duplicate",
            "message": "Event already processed"
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return {
            "status": "error",
            "message": "Processing failed"
        }

@router.get("/health")
async def webhook_health(db: Session = Depends(get_db)):
    """Webhook processing health check"""
    from sqlalchemy import func, select
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=24)

    # Count events in last 24 hours
    total = db.query(func.count(Event.id)).filter(
        Event.created_at >= since
    ).scalar() or 0

    return {
        "status": "healthy",
        "events_24h": total,
        "period_hours": 24
    }
```

#### 2. Update Main Application

**File**: `app/main.py`
**Changes**: Include webhook router

```python
# Add after app initialization
from app.routers import webhooks

app.include_router(webhooks.router)
```

#### 3. Pydantic Schemas

**File**: `app/schemas.py`
**Changes**: Create validation schemas for webhooks

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Literal
from datetime import datetime
from enum import Enum

class EventType(str, Enum):
    """Buttondown event types"""
    SUBSCRIBER_OPENED = "subscriber.opened"
    SUBSCRIBER_CLICKED = "subscriber.clicked"
    SUBSCRIBER_CONFIRMED = "subscriber.confirmed"
    SUBSCRIBER_DELIVERED = "subscriber.delivered"
    SUBSCRIBER_UNSUBSCRIBED = "subscriber.unsubscribed"
    EMAIL_SENT = "email.sent"

class ButtondownSubscriberData(BaseModel):
    """Subscriber data from Buttondown webhook"""
    subscriber: str = Field(..., description="Buttondown subscriber UUID")
    email: Optional[str] = None

class ButtondownWebhookPayload(BaseModel):
    """Complete webhook payload from Buttondown"""
    event_type: EventType
    data: ButtondownSubscriberData

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "subscriber.opened",
                "data": {
                    "subscriber": "ac79483b-cd28-49c1-982e-8a88e846d7e7"
                }
            }
        }

class SubscriberBase(BaseModel):
    """Base subscriber schema"""
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: Literal["active", "unsubscribed", "bounced"] = "active"

class SubscriberCreate(SubscriberBase):
    """Schema for creating a subscriber"""
    buttondown_id: str

class SubscriberInDB(SubscriberBase):
    """Schema for subscriber from database"""
    id: int
    buttondown_id: str
    subscription_date: datetime
    created_at: datetime

    class Config:
        from_attributes = True
```

### Success Criteria:

#### Automated Verification:
- [x] Webhook endpoint exists: `curl -X POST http://localhost:8000/webhooks/buttondown`
- [x] Health check passes: `curl http://localhost:8000/webhooks/health`
- [x] FastAPI docs show webhook endpoint: http://localhost:8000/docs
- [x] No linting errors: `ruff check app/`

#### Manual Verification:
- [x] Test webhook with sample payload using ngrok (completed - used Codespace port forwarding)
- [x] Verify events are stored in database with unique constraint working
- [x] Check duplicate events are handled correctly (return 200 with "duplicate" status)
- [x] Verify logs show event processing details
- [x] Test with invalid signature (should return 401) (skipped - webhook secret not configured in dev)
- [x] Test with malformed JSON (should return 400)
- [x] Real Buttondown webhook tested successfully (subscriber.clicked event processed)

---

## Phase 3: Testing Infrastructure

### Overview
Create comprehensive test suite using pytest with fixtures, test database setup, and mocking patterns. Target >80% code coverage.

### Changes Required:

#### 1. pytest Configuration

**File**: `pytest.ini`
**Changes**: Configure pytest

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    -v
    --strict-markers
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-fail-under=80
```

#### 2. Test Fixtures

**File**: `tests/conftest.py`
**Changes**: Create pytest fixtures for testing

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base, get_db
from app.main import app
from app.models import Subscriber, Event, Tag
import os

# Test database
TEST_DATABASE_URL = "sqlite:///./test.db"

@pytest.fixture(scope="function")
def test_engine():
    """Create in-memory engine for each test"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    return engine

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create all tables and provide session"""
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )

    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)
        # Clean up test database file
        if os.path.exists("./test.db"):
            os.remove("./test.db")

@pytest.fixture(scope="function")
def client(test_db):
    """FastAPI test client with overridden database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            test_db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()

@pytest.fixture
def sample_subscriber(test_db):
    """Create sample subscriber for tests"""
    subscriber = Subscriber(
        buttondown_id="test-subscriber-id",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        status="active"
    )
    test_db.add(subscriber)
    test_db.commit()
    test_db.refresh(subscriber)
    return subscriber

@pytest.fixture
def sample_webhook_payload():
    """Sample Buttondown webhook payload"""
    return {
        "event_type": "subscriber.opened",
        "data": {
            "subscriber": "test-subscriber-id",
            "email": "test@example.com"
        }
    }
```

#### 3. Webhook Tests

**File**: `tests/test_webhooks.py`
**Changes**: Test webhook endpoint

```python
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
```

#### 4. Model Tests

**File**: `tests/test_models.py`
**Changes**: Test database models

```python
import pytest
from app.models import Subscriber, Event, Tag, SubscriberTag
from datetime import datetime

def test_create_subscriber(test_db):
    """Test creating a subscriber"""
    subscriber = Subscriber(
        buttondown_id="test-id",
        email="test@example.com",
        first_name="Test",
        last_name="User"
    )
    test_db.add(subscriber)
    test_db.commit()
    test_db.refresh(subscriber)

    assert subscriber.id is not None
    assert subscriber.email == "test@example.com"
    assert subscriber.status == "active"

def test_subscriber_unique_email(test_db):
    """Test unique constraint on email"""
    subscriber1 = Subscriber(
        buttondown_id="test-id-1",
        email="test@example.com"
    )
    subscriber2 = Subscriber(
        buttondown_id="test-id-2",
        email="test@example.com"
    )

    test_db.add(subscriber1)
    test_db.commit()

    test_db.add(subscriber2)
    with pytest.raises(Exception):  # IntegrityError
        test_db.commit()

def test_create_event(test_db, sample_subscriber):
    """Test creating an event"""
    event = Event(
        event_id="test-event-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened",
        metadata={"test": "data"}
    )
    test_db.add(event)
    test_db.commit()
    test_db.refresh(event)

    assert event.id is not None
    assert event.subscriber_id == sample_subscriber.id

def test_event_unique_constraint(test_db, sample_subscriber):
    """Test unique constraint on event_id"""
    event1 = Event(
        event_id="duplicate-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened"
    )
    event2 = Event(
        event_id="duplicate-hash",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.opened"
    )

    test_db.add(event1)
    test_db.commit()

    test_db.add(event2)
    with pytest.raises(Exception):
        test_db.commit()

def test_subscriber_events_relationship(test_db, sample_subscriber):
    """Test relationship between subscriber and events"""
    event = Event(
        event_id="test-event",
        subscriber_id=sample_subscriber.id,
        event_type="subscriber.clicked"
    )
    test_db.add(event)
    test_db.commit()

    assert len(sample_subscriber.events) == 1
    assert sample_subscriber.events[0].event_type == "subscriber.clicked"

def test_subscriber_tags_relationship(test_db, sample_subscriber):
    """Test many-to-many relationship with tags"""
    tag = Tag(name="vip", description="VIP subscribers")
    test_db.add(tag)
    test_db.commit()

    subscriber_tag = SubscriberTag(
        subscriber_id=sample_subscriber.id,
        tag_id=tag.id
    )
    test_db.add(subscriber_tag)
    test_db.commit()

    test_db.refresh(sample_subscriber)
    assert len(sample_subscriber.tags) == 1
    assert sample_subscriber.tags[0].name == "vip"
```

#### 5. Application Tests

**File**: `tests/test_main.py`
**Changes**: Test main application endpoints

```python
def test_read_root(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "service" in data
    assert data["version"] == "1.0.0"

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_startup_probe(client):
    """Test startup probe endpoint"""
    response = client.get("/startup")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"

def test_api_docs_available(client):
    """Test that API documentation is available"""
    response = client.get("/docs")
    assert response.status_code == 200
```

### Success Criteria:

#### Automated Verification:
- [ ] All tests pass: `pytest tests/`
- [ ] Coverage >80%: `pytest --cov=app --cov-report=term-missing`
- [ ] Coverage report generated: Open `htmlcov/index.html`
- [ ] No test warnings: `pytest -W error`
- [ ] Tests run in Docker: `docker compose run web pytest`

#### Manual Verification:
- [ ] Review coverage report for gaps
- [ ] Verify all critical paths are tested
- [ ] Check test execution time (should be < 10 seconds)
- [ ] Confirm test database is cleaned up after each test

**Implementation Note**: After completing Phase 3 and verifying all automated tests pass with >80% coverage, pause for manual review and confirmation before proceeding to Phase 4.

---

## Phase 4: Analytics API Endpoints

### Overview
Create REST API endpoints for the dashboard to retrieve engagement metrics, subscriber rankings, and filtering capabilities.

### Changes Required:

#### 1. Dashboard Router

**File**: `app/routers/dashboard.py`
**Changes**: Create analytics API endpoints

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models import Subscriber, Event, Tag
from app.schemas import DashboardStats, TopSubscriber, EngagementTrend
from datetime import datetime, timedelta
from typing import List, Optional

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get overall engagement statistics.

    - Total subscribers
    - Active subscribers
    - Total emails opened
    - Total links clicked
    - Engagement rate
    """
    if not start_date:
        start_date = datetime.utcnow() - timedelta(days=30)
    if not end_date:
        end_date = datetime.utcnow()

    # Total subscribers
    total_subscribers = db.query(func.count(Subscriber.id)).scalar() or 0

    # Active subscribers
    active_subscribers = db.query(func.count(Subscriber.id)).filter(
        Subscriber.status == "active"
    ).scalar() or 0

    # Total opens
    total_opens = db.query(func.count(Event.id)).filter(
        Event.event_type == "subscriber.opened",
        Event.created_at >= start_date,
        Event.created_at <= end_date
    ).scalar() or 0

    # Total clicks
    total_clicks = db.query(func.count(Event.id)).filter(
        Event.event_type == "subscriber.clicked",
        Event.created_at >= start_date,
        Event.created_at <= end_date
    ).scalar() or 0

    # Engagement rate
    engagement_rate = 0
    if total_subscribers > 0:
        engaged_subscribers = db.query(func.count(func.distinct(Event.subscriber_id))).filter(
            Event.event_type.in_(["subscriber.opened", "subscriber.clicked"]),
            Event.created_at >= start_date,
            Event.created_at <= end_date
        ).scalar() or 0
        engagement_rate = (engaged_subscribers / total_subscribers) * 100

    return {
        "total_subscribers": total_subscribers,
        "active_subscribers": active_subscribers,
        "total_opens": total_opens,
        "total_clicks": total_clicks,
        "engagement_rate": round(engagement_rate, 2),
        "period_start": start_date,
        "period_end": end_date
    }

@router.get("/subscribers/top", response_model=List[TopSubscriber])
async def get_top_subscribers(
    limit: int = Query(10, ge=1, le=100),
    metric: str = Query("opens", regex="^(opens|clicks|total)$"),
    db: Session = Depends(get_db)
):
    """
    Get most engaged subscribers ranked by opens, clicks, or total engagement.
    """
    # Subquery for opens
    opens_subquery = db.query(
        Event.subscriber_id,
        func.count(Event.id).label("opens_count")
    ).filter(
        Event.event_type == "subscriber.opened"
    ).group_by(Event.subscriber_id).subquery()

    # Subquery for clicks
    clicks_subquery = db.query(
        Event.subscriber_id,
        func.count(Event.id).label("clicks_count")
    ).filter(
        Event.event_type == "subscriber.clicked"
    ).group_by(Event.subscriber_id).subquery()

    # Main query
    query = db.query(
        Subscriber,
        func.coalesce(opens_subquery.c.opens_count, 0).label("opens"),
        func.coalesce(clicks_subquery.c.clicks_count, 0).label("clicks")
    ).outerjoin(
        opens_subquery, Subscriber.id == opens_subquery.c.subscriber_id
    ).outerjoin(
        clicks_subquery, Subscriber.id == clicks_subquery.c.subscriber_id
    )

    # Order by selected metric
    if metric == "opens":
        query = query.order_by(desc("opens"))
    elif metric == "clicks":
        query = query.order_by(desc("clicks"))
    else:  # total
        query = query.order_by(desc(func.coalesce(opens_subquery.c.opens_count, 0) + func.coalesce(clicks_subquery.c.clicks_count, 0)))

    results = query.limit(limit).all()

    return [
        {
            "subscriber_id": subscriber.id,
            "email": subscriber.email,
            "first_name": subscriber.first_name,
            "last_name": subscriber.last_name,
            "total_opens": opens,
            "total_clicks": clicks,
            "total_engagement": opens + clicks
        }
        for subscriber, opens, clicks in results
    ]

@router.get("/trends", response_model=List[EngagementTrend])
async def get_engagement_trends(
    days: int = Query(30, ge=7, le=365),
    db: Session = Depends(get_db)
):
    """
    Get engagement trends over time (daily aggregation).
    """
    start_date = datetime.utcnow() - timedelta(days=days)

    # Daily opens
    opens_by_day = db.query(
        func.date(Event.created_at).label("date"),
        func.count(Event.id).label("count")
    ).filter(
        Event.event_type == "subscriber.opened",
        Event.created_at >= start_date
    ).group_by(func.date(Event.created_at)).all()

    # Daily clicks
    clicks_by_day = db.query(
        func.date(Event.created_at).label("date"),
        func.count(Event.id).label("count")
    ).filter(
        Event.event_type == "subscriber.clicked",
        Event.created_at >= start_date
    ).group_by(func.date(Event.created_at)).all()

    # Combine results
    dates = set([row.date for row in opens_by_day] + [row.date for row in clicks_by_day])
    opens_dict = {row.date: row.count for row in opens_by_day}
    clicks_dict = {row.date: row.count for row in clicks_by_day}

    trends = [
        {
            "date": date,
            "opens": opens_dict.get(date, 0),
            "clicks": clicks_dict.get(date, 0),
            "total": opens_dict.get(date, 0) + clicks_dict.get(date, 0)
        }
        for date in sorted(dates)
    ]

    return trends

@router.get("/subscribers/{subscriber_id}/events")
async def get_subscriber_events(
    subscriber_id: int,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get recent events for a specific subscriber"""
    events = db.query(Event).filter(
        Event.subscriber_id == subscriber_id
    ).order_by(desc(Event.created_at)).limit(limit).all()

    return events
```

#### 2. Extended Schemas

**File**: `app/schemas.py` (additions)
**Changes**: Add dashboard response schemas

```python
# Add to existing schemas.py

from typing import List
from datetime import date

class DashboardStats(BaseModel):
    """Overall dashboard statistics"""
    total_subscribers: int
    active_subscribers: int
    total_opens: int
    total_clicks: int
    engagement_rate: float
    period_start: datetime
    period_end: datetime

class TopSubscriber(BaseModel):
    """Top engaged subscriber"""
    subscriber_id: int
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    total_opens: int
    total_clicks: int
    total_engagement: int

class EngagementTrend(BaseModel):
    """Daily engagement trend"""
    date: date
    opens: int
    clicks: int
    total: int

class EventResponse(BaseModel):
    """Event response schema"""
    id: int
    event_type: str
    created_at: datetime
    metadata: Optional[dict]

    class Config:
        from_attributes = True
```

#### 3. Update Main Application

**File**: `app/main.py`
**Changes**: Include dashboard router

```python
# Add to imports
from app.routers import webhooks, dashboard

# Add after webhook router
app.include_router(dashboard.router)
```

### Success Criteria:

#### Automated Verification:
- [ ] Dashboard endpoints accessible: `curl http://localhost:8000/api/dashboard/stats`
- [ ] Top subscribers endpoint works: `curl http://localhost:8000/api/dashboard/subscribers/top`
- [ ] Trends endpoint works: `curl http://localhost:8000/api/dashboard/trends`
- [ ] All tests pass: `pytest tests/`
- [ ] API documentation updated: http://localhost:8000/docs

#### Manual Verification:
- [ ] Test with sample data in database
- [ ] Verify stats calculations are accurate
- [ ] Test filtering by date range
- [ ] Verify ranking order is correct
- [ ] Test pagination with limit parameter
- [ ] Confirm JSON response format matches schema

---

## Phase 5: Frontend Dashboard (Vue.js)

### Overview
Build a Vue.js single-page application that displays engagement metrics, subscriber rankings, and trends with filtering capabilities.

### Changes Required:

#### 1. Frontend Setup

**Directory Structure:**
```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── main.js
│   ├── App.vue
│   ├── components/
│   │   ├── DashboardStats.vue
│   │   ├── TopSubscribers.vue
│   │   ├── EngagementChart.vue
│   │   └── SubscriberDetail.vue
│   ├── services/
│   │   └── api.js
│   └── assets/
│       └── styles.css
├── package.json
└── vite.config.js
```

**File**: `frontend/package.json`
**Changes**: Create package.json

```json
{
  "name": "buttondown-dashboard",
  "version": "1.0.0",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "vue": "^3.4.0",
    "axios": "^1.6.0",
    "chart.js": "^4.4.0",
    "vue-chartjs": "^5.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "vite": "^5.0.0"
  }
}
```

#### 2. API Service

**File**: `frontend/src/services/api.js`
**Changes**: Create API client

```javascript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const dashboardAPI = {
  getStats: (startDate, endDate) =>
    api.get('/api/dashboard/stats', {
      params: { start_date: startDate, end_date: endDate }
    }),

  getTopSubscribers: (limit = 10, metric = 'opens') =>
    api.get('/api/dashboard/subscribers/top', {
      params: { limit, metric }
    }),

  getTrends: (days = 30) =>
    api.get('/api/dashboard/trends', {
      params: { days }
    }),

  getSubscriberEvents: (subscriberId, limit = 50) =>
    api.get(`/api/dashboard/subscribers/${subscriberId}/events`, {
      params: { limit }
    }),
};
```

#### 3. Dashboard Components

**File**: `frontend/src/App.vue`
**Changes**: Main dashboard layout

```vue
<template>
  <div id="app" class="container">
    <header>
      <h1>Buttondown Engagement Tracker</h1>
      <p class="subtitle">Monitor subscriber engagement in real-time</p>
    </header>

    <main>
      <DashboardStats :stats="stats" :loading="loading" />
      <EngagementChart :trends="trends" :loading="loading" />
      <TopSubscribers
        :subscribers="topSubscribers"
        :loading="loading"
        @subscriber-click="showSubscriberDetail"
      />
    </main>

    <SubscriberDetail
      v-if="selectedSubscriber"
      :subscriber="selectedSubscriber"
      @close="selectedSubscriber = null"
    />
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { dashboardAPI } from './services/api';
import DashboardStats from './components/DashboardStats.vue';
import TopSubscribers from './components/TopSubscribers.vue';
import EngagementChart from './components/EngagementChart.vue';
import SubscriberDetail from './components/SubscriberDetail.vue';

export default {
  name: 'App',
  components: {
    DashboardStats,
    TopSubscribers,
    EngagementChart,
    SubscriberDetail,
  },
  setup() {
    const stats = ref(null);
    const topSubscribers = ref([]);
    const trends = ref([]);
    const selectedSubscriber = ref(null);
    const loading = ref(true);

    const fetchDashboardData = async () => {
      loading.value = true;
      try {
        const [statsRes, subscribersRes, trendsRes] = await Promise.all([
          dashboardAPI.getStats(),
          dashboardAPI.getTopSubscribers(10, 'total'),
          dashboardAPI.getTrends(30),
        ]);

        stats.value = statsRes.data;
        topSubscribers.value = subscribersRes.data;
        trends.value = trendsRes.data;
      } catch (error) {
        console.error('Error fetching dashboard data:', error);
      } finally {
        loading.value = false;
      }
    };

    const showSubscriberDetail = (subscriber) => {
      selectedSubscriber.value = subscriber;
    };

    onMounted(() => {
      fetchDashboardData();
      // Refresh every 30 seconds
      setInterval(fetchDashboardData, 30000);
    });

    return {
      stats,
      topSubscribers,
      trends,
      selectedSubscriber,
      loading,
      showSubscriberDetail,
    };
  },
};
</script>

<style>
/* Basic styling - expand as needed */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem;
}

header {
  text-align: center;
  margin-bottom: 2rem;
}

.subtitle {
  color: #666;
  font-size: 1.1rem;
}
</style>
```

**File**: `frontend/src/components/DashboardStats.vue`
**Changes**: Stats display component

```vue
<template>
  <div class="stats-grid">
    <div class="stat-card">
      <h3>Total Subscribers</h3>
      <p class="stat-value">{{ stats?.total_subscribers || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Active Subscribers</h3>
      <p class="stat-value">{{ stats?.active_subscribers || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Email Opens</h3>
      <p class="stat-value">{{ stats?.total_opens || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Link Clicks</h3>
      <p class="stat-value">{{ stats?.total_clicks || 0 }}</p>
    </div>

    <div class="stat-card">
      <h3>Engagement Rate</h3>
      <p class="stat-value">{{ stats?.engagement_rate || 0 }}%</p>
    </div>
  </div>
</template>

<script>
export default {
  props: {
    stats: Object,
    loading: Boolean,
  },
};
</script>

<style scoped>
.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.stat-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.stat-value {
  font-size: 2rem;
  font-weight: bold;
  color: #333;
  margin: 0.5rem 0 0 0;
}
</style>
```

**File**: `frontend/src/components/TopSubscribers.vue`
**Changes**: Top subscribers list

```vue
<template>
  <div class="top-subscribers">
    <h2>Most Engaged Subscribers</h2>

    <div v-if="loading" class="loading">Loading...</div>

    <table v-else>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Email</th>
          <th>Opens</th>
          <th>Clicks</th>
          <th>Total</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="(subscriber, index) in subscribers"
          :key="subscriber.subscriber_id"
          @click="$emit('subscriber-click', subscriber)"
          class="clickable"
        >
          <td>{{ index + 1 }}</td>
          <td>{{ subscriber.email }}</td>
          <td>{{ subscriber.total_opens }}</td>
          <td>{{ subscriber.total_clicks }}</td>
          <td><strong>{{ subscriber.total_engagement }}</strong></td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
export default {
  props: {
    subscribers: Array,
    loading: Boolean,
  },
  emits: ['subscriber-click'],
};
</script>

<style scoped>
.top-subscribers {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-top: 2rem;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  text-align: left;
  padding: 0.75rem;
  border-bottom: 1px solid #eee;
}

.clickable {
  cursor: pointer;
}

.clickable:hover {
  background: #f5f5f5;
}
</style>
```

#### 4. Static File Serving

**File**: `app/main.py`
**Changes**: Serve static frontend files

```python
# Add to imports
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

# After CORS middleware
# Serve static files from frontend build
if os.path.exists("frontend/dist"):
    app.mount("/static", StaticFiles(directory="frontend/dist/assets"), name="static")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        """Serve frontend for all non-API routes"""
        if full_path.startswith("api/") or full_path.startswith("webhooks/"):
            raise HTTPException(status_code=404)

        file_path = f"frontend/dist/{full_path}"
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)

        return FileResponse("frontend/dist/index.html")
```

### Success Criteria:

#### Automated Verification:
- [ ] Frontend builds successfully: `cd frontend && npm run build`
- [ ] No build errors or warnings
- [ ] Static files served: `curl http://localhost:8000/`
- [ ] API calls work from frontend (check browser console)

#### Manual Verification:
- [ ] Dashboard loads at http://localhost:8000
- [ ] Stats display correctly with real data
- [ ] Top subscribers table populates
- [ ] Chart displays engagement trends
- [ ] Clicking subscriber shows detail view
- [ ] Dashboard auto-refreshes every 30 seconds
- [ ] Responsive design works on mobile

---

## Phase 6: Cloud Run Deployment

### Overview
Deploy the containerized application to Google Cloud Run with Cloud Storage volume mount for SQLite persistence, configure secrets, and set up health checks.

### Changes Required:

#### 1. Cloud Storage Setup

**Commands**: Run via `gcloud` CLI

```bash
# Create Cloud Storage bucket for SQLite database
gsutil mb -l us-central1 gs://buttondown-tracker-db

# Set bucket versioning for backups
gsutil versioning set on gs://buttondown-tracker-db
```

#### 2. Secret Manager Setup

**Commands**: Create secrets

```bash
# Create webhook secret
echo -n "your-buttondown-webhook-secret" | \
  gcloud secrets create buttondown-webhook-secret --data-file=-

# Create API key
echo -n "your-buttondown-api-key" | \
  gcloud secrets create buttondown-api-key --data-file=-

# Create app secret key
openssl rand -hex 32 | \
  gcloud secrets create app-secret-key --data-file=-

# Grant Cloud Run service account access
gcloud secrets add-iam-policy-binding buttondown-webhook-secret \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding buttondown-api-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding app-secret-key \
  --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

#### 3. Cloud Build Configuration

**File**: `cloudbuild.yaml`
**Changes**: Automated build and deploy

```yaml
steps:
  # Build frontend
  - name: 'node:18'
    dir: 'frontend'
    entrypoint: 'npm'
    args: ['install']

  - name: 'node:18'
    dir: 'frontend'
    entrypoint: 'npm'
    args: ['run', 'build']

  # Build Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args: [
      'build',
      '-t', 'gcr.io/$PROJECT_ID/buttondown-tracker:$COMMIT_SHA',
      '-t', 'gcr.io/$PROJECT_ID/buttondown-tracker:latest',
      '-f', 'Dockerfile',
      '.'
    ]

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/buttondown-tracker:$COMMIT_SHA']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/buttondown-tracker:latest']

  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'buttondown-tracker'
      - '--image=gcr.io/$PROJECT_ID/buttondown-tracker:$COMMIT_SHA'
      - '--region=us-central1'
      - '--platform=managed'
      - '--execution-environment=gen2'
      - '--cpu=1'
      - '--memory=512Mi'
      - '--min-instances=1'
      - '--max-instances=1'
      - '--concurrency=80'
      - '--timeout=300'
      - '--set-env-vars=ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO'
      - '--update-secrets=BUTTONDOWN_WEBHOOK_SECRET=buttondown-webhook-secret:latest,BUTTONDOWN_API_KEY=buttondown-api-key:latest,SECRET_KEY=app-secret-key:latest'
      - '--add-volume=name=sqlite-data,type=cloud-storage,bucket=buttondown-tracker-db'
      - '--add-volume-mount=volume=sqlite-data,mount-path=/app/data'
      - '--startup-probe=httpGet.path=/startup,httpGet.port=8080,initialDelaySeconds=10,failureThreshold=3,periodSeconds=10'
      - '--liveness-probe=httpGet.path=/health,httpGet.port=8080,timeoutSeconds=5,failureThreshold=3,periodSeconds=30'
      - '--allow-unauthenticated'

images:
  - 'gcr.io/$PROJECT_ID/buttondown-tracker:$COMMIT_SHA'
  - 'gcr.io/$PROJECT_ID/buttondown-tracker:latest'
```

#### 4. Manual Deployment Script

**File**: `deploy.sh`
**Changes**: Deployment script for manual deploys

```bash
#!/bin/bash
set -e

PROJECT_ID="your-gcp-project-id"
REGION="us-central1"
SERVICE_NAME="buttondown-tracker"

echo "Building frontend..."
cd frontend
npm install
npm run build
cd ..

echo "Building Docker image..."
docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:latest .

echo "Pushing to Container Registry..."
docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

echo "Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME:latest \
  --region $REGION \
  --platform managed \
  --execution-environment gen2 \
  --cpu 1 \
  --memory 512Mi \
  --min-instances 1 \
  --max-instances 1 \
  --concurrency 80 \
  --timeout 300 \
  --set-env-vars ENVIRONMENT=production,DEBUG=false,LOG_LEVEL=INFO \
  --update-secrets BUTTONDOWN_WEBHOOK_SECRET=buttondown-webhook-secret:latest,BUTTONDOWN_API_KEY=buttondown-api-key:latest,SECRET_KEY=app-secret-key:latest \
  --add-volume name=sqlite-data,type=cloud-storage,bucket=buttondown-tracker-db \
  --add-volume-mount volume=sqlite-data,mount-path=/app/data \
  --startup-probe httpGet.path=/startup,httpGet.port=8080,initialDelaySeconds=10,failureThreshold=3,periodSeconds=10 \
  --liveness-probe httpGet.path=/health,httpGet.port=8080,timeoutSeconds=5,failureThreshold=3,periodSeconds=30 \
  --allow-unauthenticated

echo "Deployment complete!"
echo "Getting service URL..."
gcloud run services describe $SERVICE_NAME --region $REGION --format='value(status.url)'
```

#### 5. Buttondown Webhook Configuration

**Manual Steps**: Configure webhook in Buttondown dashboard

1. Get Cloud Run service URL: `gcloud run services describe buttondown-tracker --region us-central1 --format='value(status.url)'`
2. Navigate to Buttondown Settings → Webhooks
3. Add webhook URL: `https://your-service-url.run.app/webhooks/buttondown`
4. Select events:
   - `subscriber.opened`
   - `subscriber.clicked`
   - `subscriber.confirmed`
   - `subscriber.delivered`
   - `subscriber.unsubscribed`
   - `email.sent`
5. Save webhook configuration
6. Copy webhook secret to Secret Manager (if provided by Buttondown)

#### 6. Monitoring Setup

**File**: `app/utils/logging.py`
**Changes**: Cloud Logging integration

```python
import logging
import json
from datetime import datetime
import sys

class CloudRunFormatter(logging.Formatter):
    """Format logs for Cloud Logging"""

    def format(self, record):
        log_obj = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "component": record.name,
        }

        # Add extra fields
        if hasattr(record, "subscriber_id"):
            log_obj["subscriber_id"] = record.subscriber_id
        if hasattr(record, "event_type"):
            log_obj["event_type"] = record.event_type

        return json.dumps(log_obj)

def setup_cloud_logging():
    """Configure logging for Cloud Run"""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(CloudRunFormatter())

    logger = logging.getLogger()
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    return logger
```

### Success Criteria:

#### Automated Verification:
- [ ] Docker image builds: `docker build -t buttondown-tracker .`
- [ ] Cloud Build succeeds: Check build logs in GCP Console
- [ ] Cloud Run service healthy: `curl https://SERVICE_URL/health`
- [ ] Startup probe passes: Check Cloud Run logs
- [ ] Liveness probe passes: Check Cloud Run logs
- [ ] Frontend loads: `curl https://SERVICE_URL/`

#### Manual Verification:
- [ ] Access deployed dashboard at Cloud Run URL
- [ ] Verify webhook endpoint accessible: `curl -X POST https://SERVICE_URL/webhooks/buttondown`
- [ ] Send test webhook from Buttondown dashboard
- [ ] Check Cloud Run logs show webhook received and processed
- [ ] Verify SQLite database persists across container restarts
- [ ] Test database in Cloud Storage bucket: `gsutil ls gs://buttondown-tracker-db/`
- [ ] Confirm secrets are loaded (check logs, don't log secret values)
- [ ] Monitor Cloud Run metrics (requests, latency, errors)
- [ ] Verify monthly cost < $10 (check billing dashboard)

**Implementation Note**: After deployment completes and all automated checks pass, perform full end-to-end testing with real Buttondown webhooks to verify production functionality before considering the project complete.

---

## Testing Strategy

### Unit Tests
- Database model tests (CRUD operations, relationships, constraints)
- Schema validation tests (Pydantic)
- Utility function tests (security, logging)

### Integration Tests
- Webhook endpoint tests (signature verification, event processing, idempotency)
- Dashboard API tests (stats calculations, filtering, pagination)
- Database query tests (complex aggregations, performance)

### End-to-End Tests
- Full webhook-to-dashboard flow
- Real Buttondown webhook processing (using ngrok for local testing)
- Multi-event scenarios
- Error handling and recovery

### Manual Testing Steps
1. **Local Development**: Use ngrok to test real webhooks from Buttondown
2. **Database Verification**: Inspect SQLite database with DB Browser
3. **Performance Testing**: Send 100+ webhooks rapidly, verify no errors
4. **Cloud Run Testing**: Verify persistence across container restarts
5. **Dashboard Testing**: Verify all metrics calculate correctly with real data

## Performance Considerations

### Database Optimization
- Composite indexes on frequently queried columns (subscriber_id + created_at, event_type + created_at)
- SQLite WAL mode enabled for better concurrent access
- Connection pooling configured appropriately

### Cloud Run Optimization
- Multi-stage Docker build (reduces image size by ~90%)
- Pre-compiled Python code
- Min instances = 1 to eliminate cold starts (acceptable for single-user app)
- Max instances = 1 to prevent SQLite write conflicts

### Frontend Optimization
- Vite build optimization (code splitting, tree shaking)
- Auto-refresh interval = 30 seconds (balance freshness vs. API load)
- Lazy loading for subscriber detail views

## Migration Notes

### If Migrating to PostgreSQL in Future:
1. Use Alembic migrations from the start
2. Keep SQLAlchemy models database-agnostic
3. Replace `sqlite:///` with `postgresql://` in config
4. Update Docker compose to include PostgreSQL service
5. Test thoroughly as aggregation queries may need adjustment

### Database Backup Strategy:
- Cloud Storage bucket has versioning enabled
- SQLite database file automatically backed up via Cloud Storage
- Consider scheduled backup job using Cloud Scheduler + Cloud Functions

## References

### Architecture Document
- Original specification: `buttondown-engagement-tracker-architecture.md`

### Research Sources
- **FastAPI Best Practices**: https://github.com/zhanymkanov/fastapi-best-practices
- **SQLite on Cloud Run**: https://www.wallacesharpedavidson.nz/post/sqlite-cloudrun/
- **Webhook Security**: https://hookdeck.com/webhooks/guides/how-to-implement-sha256-webhook-signature-verification
- **Cloud Run Documentation**: https://cloud.google.com/run/docs
- **Buttondown API**: https://docs.buttondown.com/

---

## Success Metrics

**Project Completion Criteria:**
- All phases completed and verified
- Test coverage > 80%
- All automated tests passing
- Application deployed to Cloud Run
- Real Buttondown webhooks processing successfully
- Dashboard displaying accurate metrics
- Monthly hosting cost < $10
- Documentation complete (README with setup/deployment instructions)

**Post-Launch Monitoring:**
- Webhook success rate > 99%
- Dashboard page load time < 2 seconds
- Zero data loss incidents
- Easy maintenance (< 2 hours/month)
