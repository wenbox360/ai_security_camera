"""FastAPI entry point for the security-camera cloud service."""

import json
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from typing import Optional

import boto3
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, verify_api_key, verify_token
from .config import settings
from .database import SecurityEvent, get_db, initialize_database
from .storage import generate_presigned_url, upload_to_s3
from .tasks.llm_analysis import analyze_security_event

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize_database()
    yield


app = FastAPI(
    title="AI Security Camera Cloud API",
    description="Cloud backend for AI security camera system",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
security = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    username: str
    password: str


@lru_cache(maxsize=1)
def get_s3_client():
    """Build the S3 client lazily so imports and local tests never need AWS."""
    return boto3.client("s3", region_name=settings.aws_region)


def require_bearer(credentials: Optional[HTTPAuthorizationCredentials]) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token required"
        )
    return credentials.credentials


def parse_json(value: str, expected_type: type, field_name: str):
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422, detail=f"{field_name} must be valid JSON"
        ) from exc
    if not isinstance(parsed, expected_type):
        raise HTTPException(
            status_code=422, detail=f"{field_name} has an invalid shape"
        )
    return parsed


def parse_detected_at(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="detected_at must be ISO 8601"
        ) from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def serialize_event(event: SecurityEvent, s3_client) -> dict:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "confidence_score": event.confidence_score,
        "image_url": generate_presigned_url(
            event.image_url, s3_client, settings.s3_bucket_name
        )
        if event.image_url
        else None,
        "video_url": generate_presigned_url(
            event.video_url, s3_client, settings.s3_bucket_name
        )
        if event.video_url
        else None,
        "detected_at": event.detected_at,
        "alert_triggered": event.alert_triggered,
        "alert_reason": event.alert_reason,
        "llm_analysis": json.loads(event.llm_analysis) if event.llm_analysis else None,
        "device_name": event.device.name,
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc)}


@app.post("/api/v1/auth/login")
async def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(payload.username, payload.password, db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "access_token": create_access_token({"sub": user.username}),
        "token_type": "bearer",
    }


@app.post("/api/v1/events", status_code=status.HTTP_201_CREATED)
async def create_security_event(
    event_type: str = Form(...),
    confidence_score: float = Form(...),
    detected_at: str = Form(...),
    detected_objects: str = Form("[]"),
    face_analysis: str = Form("{}"),
    image: UploadFile = File(...),
    video: Optional[UploadFile] = File(None),
    device_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    device = verify_api_key(require_bearer(device_credentials), db)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    objects = parse_json(detected_objects, list, "detected_objects")
    faces = parse_json(face_analysis, dict, "face_analysis")
    detected_time = parse_detected_at(detected_at)
    event_id, s3_client = str(uuid.uuid4()), get_s3_client()
    try:
        image_url = upload_to_s3(
            image.file,
            f"events/{event_id}/image.jpg",
            s3_client,
            settings.s3_bucket_name,
        )
        video_url = (
            upload_to_s3(
                video.file,
                f"events/{event_id}/video.mp4",
                s3_client,
                settings.s3_bucket_name,
            )
            if video
            else None
        )
        db.add(
            SecurityEvent(
                event_id=event_id,
                device_id=device.id,
                event_type=event_type,
                confidence_score=confidence_score,
                image_url=image_url,
                video_url=video_url,
                detected_objects=json.dumps(objects),
                face_analysis=json.dumps(faces),
                detected_at=detected_time,
            )
        )
        db.commit()
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Unable to persist security event")
        raise HTTPException(
            status_code=500, detail="Unable to create security event"
        ) from exc
    response = {"event_id": event_id, "status": "created", "analysis_task_id": None}
    try:
        response["analysis_task_id"] = analyze_security_event.delay(event_id).id
    except Exception:
        logger.exception(
            "Event %s was saved but could not be queued for analysis", event_id
        )
        response["analysis_status"] = "queue_unavailable"
    return response


@app.get("/api/v1/devices/{device_id}/settings")
async def get_device_settings(
    device_id: str,
    device_credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    device = verify_api_key(require_bearer(device_credentials), db)
    if not device or device.device_id != device_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device credentials",
        )
    return {
        "device_id": device.device_id,
        "notification_preferences": json.loads(device.notification_preferences)
        if device.notification_preferences
        else {},
        "detection_sensitivity": device.detection_sensitivity,
        "face_embeddings": [
            {"id": item.id, "name": item.name, "embedding": json.loads(item.embedding)}
            for item in (device.owner.face_embeddings if device.owner else [])
        ],
    }


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials], db: Session):
    user = verify_token(require_bearer(credentials), db)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )
    return user


@app.get("/api/v1/events")
async def get_events(
    skip: int = 0,
    limit: int = 50,
    alert_only: bool = False,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    if skip < 0 or not 1 <= limit <= 100:
        raise HTTPException(
            status_code=422,
            detail="skip must be non-negative and limit must be between 1 and 100",
        )
    device_ids = [device.id for device in get_current_user(credentials, db).devices]
    query = db.query(SecurityEvent).filter(SecurityEvent.device_id.in_(device_ids))
    if alert_only:
        query = query.filter(SecurityEvent.alert_triggered.is_(True))
    s3_client = get_s3_client()
    return [
        serialize_event(event, s3_client)
        for event in query.order_by(SecurityEvent.detected_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    ]


@app.get("/api/v1/events/{event_id}")
async def get_event_details(
    event_id: str,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
):
    device_ids = [device.id for device in get_current_user(credentials, db).devices]
    event = (
        db.query(SecurityEvent)
        .filter(
            SecurityEvent.event_id == event_id, SecurityEvent.device_id.in_(device_ids)
        )
        .first()
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    result = serialize_event(event, get_s3_client())
    result.update(
        {
            "detected_objects": json.loads(event.detected_objects)
            if event.detected_objects
            else [],
            "face_analysis": json.loads(event.face_analysis)
            if event.face_analysis
            else {},
            "processed_at": event.processed_at,
        }
    )
    return result


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)
