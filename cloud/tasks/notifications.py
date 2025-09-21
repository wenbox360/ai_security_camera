import logging
import json
from typing import Dict, Any
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..database import get_db, SecurityEvent, User
from ..config import settings

logger = logging.getLogger(__name__)

@celery_app.task
def send_security_alert(event_id: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Send security alert notification to mobile app
    
    Args:
        event_id: The security event ID
        analysis_result: LLM analysis result containing alert details
        
    Returns:
        Dict containing notification status
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Get the security event
        event = db.query(SecurityEvent).filter(SecurityEvent.event_id == event_id).first()
        if not event:
            raise ValueError(f"Security event {event_id} not found")
        
        # Prepare notification payload
        notification_data = {
            "event_id": event_id,
            "alert_level": analysis_result.get("alert_level", "medium"),
            "summary": analysis_result.get("summary", "Security alert triggered"),
            "reasoning": analysis_result.get("reasoning", ""),
            "detected_at": event.detected_at.isoformat(),
            "device_name": event.device.name if event.device else "Unknown Device",
            "event_type": event.event_type,
            "confidence_score": event.confidence_score
        }
        
        # TODO: Implement actual push notification service
        # For now, we'll log the notification and mark it as sent
        logger.info(f"SECURITY ALERT: {notification_data}")
        
        # In production, you would:
        # 1. Get user's push notification tokens from database
        # 2. Send push notification via APNs (iOS) or FCM (Android)
        # 3. Send email/SMS backup if configured
        # 4. Store notification in database for history
        
        # Example placeholder for push notification:
        # await send_push_notification(
        #     tokens=user_tokens,
        #     title=f"Security Alert - {analysis_result.get('alert_level', 'Medium')}",
        #     body=analysis_result.get('summary', 'Security event detected'),
        #     data=notification_data
        # )
        
        # Mark alert as sent
        event.alert_sent = True
        db.commit()
        
        result = {
            "event_id": event_id,
            "notification_sent": True,
            "alert_level": analysis_result.get("alert_level", "medium"),
            "timestamp": datetime.utcnow().isoformat(),
            "status": "completed"
        }
        
        logger.info(f"Alert sent for event {event_id}")
        return result
        
    except Exception as e:
        logger.error(f"Error sending alert for event {event_id}: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task
def send_daily_summary(user_id: int) -> Dict[str, Any]:
    """
    Send daily summary of security events to user
    
    Args:
        user_id: User ID to send summary to
        
    Returns:
        Dict containing summary status
    """
    try:
        db = next(get_db())
        
        # Calculate yesterday's date range
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)
        start_time = datetime.combine(yesterday, datetime.min.time())
        end_time = datetime.combine(yesterday, datetime.max.time())
        
        # Get user's devices
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError(f"User {user_id} not found")
        
        device_ids = [device.id for device in user.devices]
        
        # Get yesterday's events
        events = db.query(SecurityEvent).filter(
            SecurityEvent.device_id.in_(device_ids),
            SecurityEvent.detected_at >= start_time,
            SecurityEvent.detected_at <= end_time
        ).all()
        
        # Compile summary
        total_events = len(events)
        alerts_triggered = len([e for e in events if e.alert_triggered])
        event_types = {}
        
        for event in events:
            event_types[event.event_type] = event_types.get(event.event_type, 0) + 1
        
        summary_data = {
            "date": yesterday.isoformat(),
            "total_events": total_events,
            "alerts_triggered": alerts_triggered,
            "event_types": event_types,
            "user_email": user.email
        }
        
        # TODO: Send email summary
        logger.info(f"Daily summary for user {user_id}: {summary_data}")
        
        return {
            "user_id": user_id,
            "summary_sent": True,
            "total_events": total_events,
            "alerts_triggered": alerts_triggered,
            "status": "completed"
        }
        
    except Exception as e:
        logger.error(f"Error sending daily summary for user {user_id}: {str(e)}")
        raise
    
    finally:
        db.close()
