from sqlalchemy import (
    Column, Integer, String, DateTime, ForeignKey,
    Index, JSON
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
    subscriber_id = Column(Integer, ForeignKey("subscribers.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    email_id = Column(String(100), nullable=True, index=True)
    link_url = Column(String(500), nullable=True)
    event_metadata = Column(JSON, nullable=True)
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


class SyncState(Base):
    __tablename__ = "sync_states"

    key = Column(String(100), primary_key=True)
    last_synced_at = Column(DateTime(timezone=True), nullable=True, index=True)
    payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
