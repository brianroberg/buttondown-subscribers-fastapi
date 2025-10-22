from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import init_db
from app.routers import webhooks
import logging
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events"""
    # Startup
    logger.info(f"Starting {settings.app_name} in {settings.environment} mode")
    init_db()
    logger.info("Database initialized")

    yield

    # Shutdown (if needed in future)
    logger.info("Shutting down application")


# Initialize FastAPI with lifespan
app = FastAPI(
    title=settings.app_name,
    description="Track and analyze Buttondown subscriber engagement",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

# Include routers
app.include_router(webhooks.router)

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
