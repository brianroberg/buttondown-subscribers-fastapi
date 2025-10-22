from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from app.database import get_db
from app.models import Subscriber, Event, Tag
from app.schemas import DashboardStats, TopSubscriber, EngagementTrend, EventResponse
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
    engagement_rate = 0.0
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
    metric: str = Query("opens", pattern="^(opens|clicks|total)$"),
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

@router.get("/subscribers/{subscriber_id}/events", response_model=List[EventResponse])
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
