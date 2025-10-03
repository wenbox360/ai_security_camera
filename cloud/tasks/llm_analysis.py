import json
import logging
from datetime import datetime
from typing import Dict, List, Any

import openai
from sqlalchemy.orm import Session

from ..celery_app import celery_app
from ..database import get_db, SecurityEvent, ProcessingTask
from ..config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure OpenAI
openai.api_key = settings.openai_api_key

@celery_app.task(bind=True)
def analyze_security_event(self, event_id: str) -> Dict[str, Any]:
    """
    Analyze a security event using OpenAI GPT-4V to determine if an alert should be triggered.
    
    Args:
        event_id: The ID of the security event to analyze
        
    Returns:
        Dict containing analysis results and alert decision
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Update task status
        task = ProcessingTask(
            task_id=self.request.id,
            event_id=event_id,
            task_type="llm_analysis",
            status="processing"
        )
        db.add(task)
        db.commit()
        
        # Get the security event
        event = db.query(SecurityEvent).filter(SecurityEvent.event_id == event_id).first()
        if not event:
            raise ValueError(f"Security event {event_id} not found")
        
        # Prepare context for LLM
        context = {
            "event_type": event.event_type,
            "confidence_score": event.confidence_score,
            "detected_objects": json.loads(event.detected_objects) if event.detected_objects else [],
            "face_analysis": json.loads(event.face_analysis) if event.face_analysis else {},
            "detected_at": event.detected_at.isoformat(),
            "device_name": event.device.name if event.device else "Unknown"
        }
        
        # Create prompt for GPT-4V
        prompt = f"""
        You are an AI security analyst reviewing a security camera event. Analyze the following information and decide if this warrants an immediate alert.
        
        Event Details:
        - Type: {context['event_type']}
        - Confidence: {context['confidence_score']}
        - Time: {context['detected_at']}
        - Device: {context['device_name']}
        - Detected Objects: {context['detected_objects']}
        - Face Analysis: {context['face_analysis']}
        
        Consider these factors:
        1. Is this a known person (face_analysis will indicate if face is recognized)
        2. Time of day (nighttime activity more suspicious)
        3. Type of objects detected
        4. Confidence levels
        5. Unusual behavior patterns
        
        Respond with a JSON object containing:
        {{
            "alert_needed": boolean,
            "alert_level": "low" | "medium" | "high",
            "reasoning": "detailed explanation of decision",
            "recommended_action": "description of what should happen",
            "summary": "brief summary for notification"
        }}
        """
        
        # Call OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a security analyst AI. Always respond with valid JSON."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.1
        )
        
        # Parse response
        analysis_result = json.loads(response.choices[0].message.content)
        
        # Update event with analysis
        event.llm_analysis = json.dumps(analysis_result)
        event.alert_triggered = analysis_result.get("alert_needed", False)
        event.alert_reason = analysis_result.get("reasoning", "")
        event.processed_at = datetime.utcnow()
        
        # Update task status
        task.status = "completed"
        task.result = json.dumps(analysis_result)
        task.completed_at = datetime.utcnow()
        
        db.commit()
        
        # If alert is needed, trigger notification task
        if analysis_result.get("alert_needed", False):
            from .notifications import send_security_alert
            send_security_alert.delay(event_id, analysis_result)
        
        logger.info(f"Successfully analyzed event {event_id}")
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error analyzing event {event_id}: {str(e)}")
        
        # Update task with error
        if 'task' in locals():
            task.status = "failed"
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            db.commit()
        
        # Re-raise for Celery
        raise self.retry(exc=e, countdown=60, max_retries=3)
    
    finally:
        db.close()

@celery_app.task
def batch_analyze_events(event_ids: List[str]) -> Dict[str, Any]:
    """
    Analyze multiple security events in batch for efficiency.
    """
    results = {}
    for event_id in event_ids:
        try:
            result = analyze_security_event.delay(event_id)
            results[event_id] = result.id
        except Exception as e:
            logger.error(f"Failed to queue analysis for event {event_id}: {str(e)}")
            results[event_id] = f"error: {str(e)}"
    
    return results
