import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import get_settings

settings = get_settings()

# Ensure SQLite directory exists before engine creation
if settings.sqlalchemy_database_url.startswith("sqlite"):
    db_dir = os.path.dirname(settings.db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

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
    # Import models to register them with SQLAlchemy
    from app.models import Subscriber, Event, Tag, SubscriberTag, SyncState  # noqa: F401
    Base.metadata.create_all(bind=engine)
