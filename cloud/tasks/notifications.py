"""Alert-recording task; external notification delivery is intentionally absent."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict

from ..celery_app import celery_app
from ..database import SecurityEvent, get_db

logger = logging.getLogger(__name__)


@celery_app.task
def record_security_alert(
    event_id: str, analysis_result: Dict[str, Any]
) -> Dict[str, Any]:
    """Record an analyzed alert without claiming delivery to an external provider."""
    db = next(get_db())
    try:
        event = (
            db.query(SecurityEvent).filter(SecurityEvent.event_id == event_id).first()
        )
        if event is None:
            raise ValueError(f"Security event {event_id} not found")

        alert_record = {
            "event_id": event_id,
            "alert_level": analysis_result.get("alert_level", "medium"),
            "summary": analysis_result.get("summary", "Security alert triggered"),
            "reasoning": analysis_result.get("reasoning", ""),
            "detected_at": event.detected_at.isoformat(),
            "device_name": event.device.name if event.device else "Unknown Device",
            "event_type": event.event_type,
            "confidence_score": event.confidence_score,
        }
        logger.info("SECURITY ALERT RECORDED: %s", alert_record)
        event.alert_sent = False
        db.commit()
        return {
            "event_id": event_id,
            "alert_recorded": True,
            "notification_sent": False,
            "delivery_status": "not_configured",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception:
        db.rollback()
        logger.exception("Unable to record alert for event %s", event_id)
        raise
    finally:
        db.close()
