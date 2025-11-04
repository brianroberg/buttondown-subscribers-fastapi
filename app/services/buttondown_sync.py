"""Synchronisation service for ingesting Buttondown engagement data."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.models import Event, Subscriber, SyncState
from app.utils.buttondown import ButtondownAPI

logger = logging.getLogger(__name__)


@dataclass
class SyncOutcome:
    """Summary of an ingestion run."""

    events_created: int
    events_skipped: int
    subscribers_created: int
    subscribers_updated: int
    requested_since: Optional[datetime]
    effective_since: Optional[datetime]
    latest_event_at: Optional[datetime]
    last_synced_at: Optional[datetime]


class ButtondownEventSynchronizer:
    """Service that ingests Buttondown email engagement events via the API."""

    STATE_KEY = "buttondown_events"
    DEFAULT_LOOKBACK_DAYS = 30

    def __init__(
        self,
        db: Session,
        client: ButtondownAPI,
        *,
        logger_: Optional[logging.Logger] = None,
        default_lookback_days: Optional[int] = None,
    ) -> None:
        self.db = db
        self.client = client
        self.logger = logger_ or logger
        self.default_lookback_days = default_lookback_days or self.DEFAULT_LOOKBACK_DAYS

    def sync(self, *, since: Optional[datetime] = None) -> SyncOutcome:
        """
        Fetch events from Buttondown and persist them locally.

        Args:
            since: Optional override start timestamp. When omitted we resume from
                the last persisted sync time or fall back to a recent lookback window.
        """
        requested_since = since
        state = self._get_or_create_state()

        effective_since = self._determine_since(state.last_synced_at, requested_since)
        self.logger.info(
            "Starting Buttondown sync (requested_since=%s, effective_since=%s)",
            requested_since,
            effective_since,
        )

        counters = {
            "events_created": 0,
            "events_skipped": 0,
            "subscribers_created": 0,
            "subscribers_updated": 0,
        }
        latest_event_at: Optional[datetime] = None

        for event in self.client.iter_events(
            since=effective_since,
            expand=["subscriber", "email"],
            ordering="creation_date",
        ):
            event_creation = self._parse_datetime(event.get("creation_date"))

            # When we fall back to client-side filtering, halt once we leave the desired window.
            if effective_since and event_creation and event_creation <= effective_since:
                continue

            created, skipped, subscriber_flags = self._persist_event(event, event_creation)

            counters["events_created"] += int(created)
            counters["events_skipped"] += int(skipped)
            counters["subscribers_created"] += int(subscriber_flags.created)
            counters["subscribers_updated"] += int(subscriber_flags.updated)

            if event_creation and (
                latest_event_at is None or event_creation > latest_event_at
            ):
                latest_event_at = event_creation

        # Commit any staged DB work before updating the sync record.
        self.db.commit()

        if latest_event_at and (state.last_synced_at is None or latest_event_at > state.last_synced_at):
            state.last_synced_at = latest_event_at
            state.updated_at = datetime.now(timezone.utc)
            self.db.add(state)
            self.db.commit()

        self.logger.info(
            "Completed Buttondown sync",
            extra={
                "events_created": counters["events_created"],
                "events_skipped": counters["events_skipped"],
                "subscribers_created": counters["subscribers_created"],
                "subscribers_updated": counters["subscribers_updated"],
                "latest_event_at": latest_event_at.isoformat() if latest_event_at else None,
                "last_synced_at": state.last_synced_at.isoformat() if state.last_synced_at else None,
            },
        )

        return SyncOutcome(
            events_created=counters["events_created"],
            events_skipped=counters["events_skipped"],
            subscribers_created=counters["subscribers_created"],
            subscribers_updated=counters["subscribers_updated"],
            requested_since=requested_since,
            effective_since=effective_since,
            latest_event_at=latest_event_at,
            last_synced_at=state.last_synced_at,
        )

    # Helpers -----------------------------------------------------------------

    def _determine_since(
        self,
        last_synced_at: Optional[datetime],
        requested_since: Optional[datetime],
    ) -> Optional[datetime]:
        if requested_since:
            return self._ensure_utc(requested_since)
        if last_synced_at:
            return self._ensure_utc(last_synced_at)
        return datetime.now(timezone.utc) - timedelta(days=self.default_lookback_days)

    def _persist_event(
        self,
        payload: dict,
        event_creation: Optional[datetime],
    ) -> Tuple[bool, bool, "SubscriberFlags"]:
        event_id = payload.get("id")
        if not event_id:
            self.logger.warning("Skipping event with no id: %s", payload)
            return False, True, SubscriberFlags(False, False)

        existing = (
            self.db.query(Event)
            .filter(Event.event_id == event_id)
            .first()
        )
        if existing:
            return False, True, SubscriberFlags(False, False)

        normalized_type = self._normalize_event_type(payload.get("event_type"))
        subscriber, subscriber_flags = self._upsert_subscriber(payload, normalized_type)

        event = Event(
            event_id=event_id,
            subscriber_id=subscriber.id if subscriber else None,
            event_type=normalized_type,
            email_id=payload.get("email_id"),
            link_url=self._extract_link(payload),
            event_metadata=payload,
            created_at=event_creation,
        )
        self.db.add(event)
        return True, False, subscriber_flags

    def _upsert_subscriber(
        self,
        event_payload: dict,
        normalized_event_type: str,
    ) -> Tuple[Optional[Subscriber], "SubscriberFlags"]:
        subscriber_id = event_payload.get("subscriber_id")
        subscriber_data = event_payload.get("subscriber") or {}
        metadata = event_payload.get("metadata") or {}

        email = (
            subscriber_data.get("email_address")
            or subscriber_data.get("email")
            or metadata.get("email")
        )

        if not subscriber_id and not email:
            # Events like automated sends can lack subscriber context.
            return None, SubscriberFlags(False, False)

        subscriber = None
        if subscriber_id:
            subscriber = (
                self.db.query(Subscriber)
                .filter(Subscriber.buttondown_id == subscriber_id)
                .first()
            )

        created = False
        updated = False

        if not subscriber:
            if not subscriber_id:
                self.logger.debug(
                    "Skipping subscriber creation because no subscriber_id provided; payload=%s",
                    event_payload,
                )
                return None, SubscriberFlags(False, False)

            email_address = email or f"{subscriber_id}@unknown.buttondown"
            subscriber = Subscriber(
                buttondown_id=subscriber_id,
                email=email_address,
                first_name=subscriber_data.get("first_name"),
                last_name=subscriber_data.get("last_name"),
                status="active",
                source=subscriber_data.get("source"),
            )
            self.db.add(subscriber)
            self.db.flush()
            created = True
        else:
            updates = {
                "email": email,
                "first_name": subscriber_data.get("first_name"),
                "last_name": subscriber_data.get("last_name"),
            }
            for field, value in updates.items():
                if value and getattr(subscriber, field) != value:
                    setattr(subscriber, field, value)
                    updated = True

        desired_status = self._infer_status_from_event(normalized_event_type)
        if desired_status and subscriber and subscriber.status != desired_status:
            subscriber.status = desired_status
            updated = True

        return subscriber, SubscriberFlags(created, updated)

    def _extract_link(self, payload: dict) -> Optional[str]:
        metadata = payload.get("metadata") or {}
        return metadata.get("url") or metadata.get("link")

    def _get_or_create_state(self) -> SyncState:
        state = (
            self.db.query(SyncState)
            .filter(SyncState.key == self.STATE_KEY)
            .first()
        )
        if not state:
            state = SyncState(key=self.STATE_KEY)
            self.db.add(state)
            self.db.commit()
            state = (
                self.db.query(SyncState)
                .filter(SyncState.key == self.STATE_KEY)
                .first()
            )
        return state

    @staticmethod
    def _normalize_event_type(event_type: Optional[str]) -> str:
        if not event_type:
            return "unknown"

        suffix_map = {
            "opened": "subscriber.opened",
            "clicked": "subscriber.clicked",
            "delivered": "subscriber.delivered",
            "sent": "email.sent",
            "unsubscribed": "subscriber.unsubscribed",
            "bounced": "subscriber.bounced",
            "complained": "subscriber.complained",
            "rejected": "subscriber.rejected",
            "replied": "subscriber.replied",
            "attempted": "email.attempted",
        }

        for suffix, normalized in suffix_map.items():
            if event_type.endswith(suffix):
                return normalized

        return event_type

    @staticmethod
    def _infer_status_from_event(event_type: str) -> Optional[str]:
        if event_type in {"subscriber.unsubscribed"}:
            return "unsubscribed"
        if event_type in {"subscriber.bounced", "subscriber.complained", "subscriber.rejected"}:
            return "bounced"
        if event_type in {
            "subscriber.opened",
            "subscriber.clicked",
            "subscriber.delivered",
            "email.sent",
            "email.attempted",
        }:
            return "active"
        return None

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _ensure_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


@dataclass
class SubscriberFlags:
    """Flags describing subscriber mutations that occurred while processing an event."""

    created: bool = False
    updated: bool = False
