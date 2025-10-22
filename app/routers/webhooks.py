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
    email = data.get("email", f"{subscriber_id}@unknown.local")

    if not subscriber_id:
        logger.warning("subscriber.opened event missing subscriber ID")
        return

    # Get or create subscriber
    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(
            buttondown_id=subscriber_id,
            email=email
        )
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

    logger.info(f"Processed email open for subscriber {subscriber_id}")

async def process_subscriber_clicked(data: dict, db: Session):
    """Process subscriber.clicked event"""
    subscriber_id = data.get("subscriber")
    email = data.get("email", f"{subscriber_id}@unknown.local")

    if not subscriber_id:
        logger.warning("subscriber.clicked event missing subscriber ID")
        return

    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(
            buttondown_id=subscriber_id,
            email=email
        )
        db.add(subscriber)
        db.commit()
        db.refresh(subscriber)

    logger.info(f"Processed link click for subscriber {subscriber_id}")

async def process_subscriber_confirmed(data: dict, db: Session):
    """Process subscriber.confirmed event"""
    subscriber_id = data.get("subscriber")
    email = data.get("email", f"{subscriber_id}@unknown.local")

    if not subscriber_id:
        logger.warning("subscriber.confirmed event missing subscriber ID")
        return

    subscriber = db.query(Subscriber).filter(
        Subscriber.buttondown_id == subscriber_id
    ).first()

    if not subscriber:
        subscriber = Subscriber(
            buttondown_id=subscriber_id,
            email=email,
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

@router.get("/buttondown")
async def buttondown_webhook_validation():
    """
    Webhook validation endpoint for Buttondown.
    Returns 200 OK so Buttondown can verify the webhook URL is valid.
    """
    return {
        "status": "ok",
        "message": "Buttondown webhook endpoint is ready"
    }

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

    # Check if event already exists
    existing_event = db.query(Event).filter(Event.event_id == event_hash).first()
    if existing_event:
        logger.info(f"Duplicate webhook ignored: {event_type}")
        return {
            "status": "duplicate",
            "message": "Event already processed"
        }

    try:
        # Process based on event type and get/create subscriber
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

        # Get subscriber ID for event record
        subscriber_buttondown_id = data.get("subscriber")
        subscriber = None
        if subscriber_buttondown_id:
            subscriber = db.query(Subscriber).filter(
                Subscriber.buttondown_id == subscriber_buttondown_id
            ).first()

        # Create event record
        event = Event(
            event_id=event_hash,
            subscriber_id=subscriber.id if subscriber else None,
            event_type=event_type,
            event_metadata=payload
        )
        db.add(event)
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
    from sqlalchemy import func
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
