"""Celery tasks for structured OpenAI analysis of security events."""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from openai import OpenAI

from ..celery_app import celery_app
from ..config import settings
from ..database import ProcessingTask, SecurityEvent, get_db

logger = logging.getLogger(__name__)


def _analysis_prompt(event: SecurityEvent) -> str:
    return json.dumps(
        {
            "event_type": event.event_type,
            "confidence_score": event.confidence_score,
            "detected_objects": json.loads(event.detected_objects)
            if event.detected_objects
            else [],
            "face_analysis": json.loads(event.face_analysis)
            if event.face_analysis
            else {},
            "detected_at": event.detected_at.isoformat(),
            "device_name": event.device.name if event.device else "Unknown",
        }
    )


def request_analysis(client: OpenAI, event: SecurityEvent) -> Dict[str, Any]:
    """Call the Responses API and require a compact, machine-readable result."""
    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "developer",
                "content": "You are a security analyst. Return only valid JSON.",
            },
            {
                "role": "user",
                "content": (
                    "Assess this camera event. Consider recognized faces, confidence, time, "
                    "objects, and suspicious behavior. Return JSON with alert_needed (boolean), "
                    "alert_level (low|medium|high), reasoning, recommended_action, and summary.\n"
                    + _analysis_prompt(event)
                ),
            },
        ],
        text={"format": {"type": "json_object"}},
    )
    raw = response.output_text
    result = json.loads(raw)
    if not isinstance(result, dict) or not isinstance(result.get("alert_needed"), bool):
        raise ValueError("OpenAI response did not contain a valid analysis object")
    return result


@celery_app.task(bind=True, autoretry_for=(), max_retries=3)
def analyze_security_event(self, event_id: str) -> Dict[str, Any]:
    db = None
    task = None
    try:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        db = next(get_db())
        task = (
            db.query(ProcessingTask)
            .filter(ProcessingTask.task_id == self.request.id)
            .first()
        )
        if task is None:
            task = ProcessingTask(
                task_id=self.request.id, event_id=event_id, task_type="llm_analysis"
            )
            db.add(task)
        task.status = "processing"
        db.commit()
        event = (
            db.query(SecurityEvent).filter(SecurityEvent.event_id == event_id).first()
        )
        if event is None:
            raise ValueError(f"Security event {event_id} not found")
        result = request_analysis(OpenAI(api_key=settings.openai_api_key), event)
        event.llm_analysis = json.dumps(result)
        event.alert_triggered = result["alert_needed"]
        event.alert_reason = result.get("reasoning", "")
        event.processed_at = datetime.now(timezone.utc)
        task.status, task.result, task.completed_at = (
            "completed",
            json.dumps(result),
            datetime.now(timezone.utc),
        )
        db.commit()
        if result["alert_needed"]:
            from .notifications import record_security_alert

            record_security_alert.delay(event_id, result)
        return result
    except Exception as exc:
        logger.exception("Security analysis failed for event %s", event_id)
        if db is not None and task is not None:
            task.status, task.error_message, task.completed_at = (
                "failed",
                str(exc),
                datetime.now(timezone.utc),
            )
            db.commit()
        raise self.retry(exc=exc, countdown=60, max_retries=3)
    finally:
        if db is not None:
            db.close()


@celery_app.task
def batch_analyze_events(event_ids: List[str]) -> Dict[str, Any]:
    return {
        event_id: analyze_security_event.delay(event_id).id for event_id in event_ids
    }
