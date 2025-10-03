from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import uuid
from datetime import datetime, timedelta
import boto3
from botocore.exceptions import ClientError

from .database import get_db, SecurityEvent, Device, User, create_tables
from .config import settings
from .auth import verify_token, verify_api_key, create_access_token
from .tasks.llm_analysis import analyze_security_event
from .storage import upload_to_s3, generate_presigned_url

# Create FastAPI app
app = FastAPI(
    title="AI Security Camera Cloud API",
    description="Cloud backend for AI security camera system",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security scheme
security = HTTPBearer()

# AWS S3 client
s3_client = boto3.client(
    's3',
    aws_access_key_id=settings.aws_access_key_id,
    aws_secret_access_key=settings.aws_secret_access_key,
    region_name=settings.aws_region
)

@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup"""
    create_tables()

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Pi Device Endpoints
@app.post("/api/v1/events")
async def create_security_event(
    event_type: str = Form(...),
    confidence_score: float = Form(...),
    detected_at: str = Form(...),
    detected_objects: str = Form("[]"),
    face_analysis: str = Form("{}"),
    image: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    device_credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Create a new security event from Pi device
    """
    # Verify Pi device
    device = verify_api_key(device_credentials.credentials, db)
    if not device:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Generate unique event ID
    event_id = str(uuid.uuid4())
    
    try:
        # Upload image to S3
        image_key = f"events/{event_id}/image.jpg"
        image_url = upload_to_s3(image.file, image_key, s3_client, settings.s3_bucket_name)
        
        # Upload video if provided
        video_url = None
        if video:
            video_key = f"events/{event_id}/video.mp4"
            video_url = upload_to_s3(video.file, video_key, s3_client, settings.s3_bucket_name)
        
        # Create security event
        event = SecurityEvent(
            event_id=event_id,
            device_id=device.id,
            event_type=event_type,
            confidence_score=confidence_score,
            image_url=image_url,
            video_url=video_url,
            detected_objects=detected_objects,
            face_analysis=face_analysis,
            detected_at=datetime.fromisoformat(detected_at.replace('Z', '+00:00')),
        )
        
        db.add(event)
        db.commit()
        db.refresh(event)
        
        # Queue LLM analysis task
        task = analyze_security_event.delay(event_id)
        
        return {
            "event_id": event_id,
            "status": "created",
            "analysis_task_id": task.id,
            "message": "Event created and queued for analysis"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create event: {str(e)}")

@app.get("/api/v1/devices/{device_id}/settings")
async def get_device_settings(
    device_id: str,
    device_credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get device settings for Pi
    """
    device = verify_api_key(device_credentials.credentials, db)
    if not device or device.device_id != device_id:
        raise HTTPException(status_code=401, detail="Invalid API key or device ID")
    
    return {
        "device_id": device.device_id,
        "notification_preferences": json.loads(device.notification_preferences) if device.notification_preferences else {},
        "detection_sensitivity": device.detection_sensitivity,
        "face_embeddings": [
            {
                "name": embedding.name,
                "embedding": json.loads(embedding.embedding)
            }
            for embedding in device.owner.face_embeddings
        ]
    }

# Mobile App Endpoints
@app.get("/api/v1/events")
async def get_events(
    skip: int = 0,
    limit: int = 50,
    alert_only: bool = False,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get security events for mobile app
    """
    user = verify_token(token.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user's devices
    device_ids = [device.id for device in user.devices]
    
    # Query events
    query = db.query(SecurityEvent).filter(SecurityEvent.device_id.in_(device_ids))
    
    if alert_only:
        query = query.filter(SecurityEvent.alert_triggered == True)
    
    events = query.order_by(SecurityEvent.detected_at.desc()).offset(skip).limit(limit).all()
    
    # Generate presigned URLs for images/videos
    for event in events:
        if event.image_url:
            event.image_url = generate_presigned_url(event.image_url, s3_client, settings.s3_bucket_name)
        if event.video_url:
            event.video_url = generate_presigned_url(event.video_url, s3_client, settings.s3_bucket_name)
    
    return [
        {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "confidence_score": event.confidence_score,
            "image_url": event.image_url,
            "video_url": event.video_url,
            "detected_at": event.detected_at,
            "alert_triggered": event.alert_triggered,
            "alert_reason": event.alert_reason,
            "llm_analysis": json.loads(event.llm_analysis) if event.llm_analysis else None,
            "device_name": event.device.name
        }
        for event in events
    ]

@app.get("/api/v1/events/{event_id}")
async def get_event_details(
    event_id: str,
    token: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """
    Get detailed information about a specific event
    """
    user = verify_token(token.credentials, db)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Get user's devices
    device_ids = [device.id for device in user.devices]
    
    event = db.query(SecurityEvent).filter(
        SecurityEvent.event_id == event_id,
        SecurityEvent.device_id.in_(device_ids)
    ).first()
    
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    # Generate presigned URLs
    image_url = generate_presigned_url(event.image_url, s3_client, settings.s3_bucket_name) if event.image_url else None
    video_url = generate_presigned_url(event.video_url, s3_client, settings.s3_bucket_name) if event.video_url else None
    
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "confidence_score": event.confidence_score,
        "image_url": image_url,
        "video_url": video_url,
        "detected_objects": json.loads(event.detected_objects) if event.detected_objects else [],
        "face_analysis": json.loads(event.face_analysis) if event.face_analysis else {},
        "llm_analysis": json.loads(event.llm_analysis) if event.llm_analysis else None,
        "detected_at": event.detected_at,
        "processed_at": event.processed_at,
        "alert_triggered": event.alert_triggered,
        "alert_reason": event.alert_reason,
        "device_name": event.device.name
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port, debug=settings.debug)
