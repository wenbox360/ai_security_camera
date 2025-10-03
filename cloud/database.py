from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid

from .config import settings

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database Models
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    devices = relationship("Device", back_populates="owner")
    face_embeddings = relationship("FaceEmbedding", back_populates="user")

class Device(Base):
    __tablename__ = "devices"
    
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String(100), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    api_key = Column(String(255), unique=True, nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Device settings (JSON stored as text)
    notification_preferences = Column(Text)  # JSON string
    detection_sensitivity = Column(Float, default=0.7)
    
    # Relationships
    owner = relationship("User", back_populates="devices")
    events = relationship("SecurityEvent", back_populates="device")

class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String(100), nullable=False)
    embedding = Column(Text, nullable=False)  # JSON array of face embedding
    image_url = Column(String(500))  # S3 URL of the reference image
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="face_embeddings")

class SecurityEvent(Base):
    __tablename__ = "security_events"
    
    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String(100), unique=True, index=True, nullable=False)
    device_id = Column(Integer, ForeignKey("devices.id"))
    
    # Event details
    event_type = Column(String(50), nullable=False)  # "person_detected", "motion", "unknown_face"
    confidence_score = Column(Float)
    
    # Media
    image_url = Column(String(500))  # S3 URL
    video_url = Column(String(500))  # S3 URL
    
    # Analysis results
    detected_objects = Column(Text)  # JSON array of detected objects
    face_analysis = Column(Text)     # JSON object of face analysis
    llm_analysis = Column(Text)      # LLM decision and reasoning
    
    # Alert decision
    alert_triggered = Column(Boolean, default=False)
    alert_sent = Column(Boolean, default=False)
    alert_reason = Column(Text)
    
    # Timestamps
    detected_at = Column(DateTime(timezone=True), nullable=False)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    device = relationship("Device", back_populates="events")

class ProcessingTask(Base):
    __tablename__ = "processing_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(100), unique=True, index=True, nullable=False)
    event_id = Column(String(100), ForeignKey("security_events.event_id"))
    task_type = Column(String(50), nullable=False)  # "llm_analysis", "face_recognition"
    status = Column(String(20), default="pending")  # "pending", "processing", "completed", "failed"
    result = Column(Text)  # JSON result
    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

# Initialize database - create all tables and setup
def initialize_database():
    """
    Initialize the database by creating all tables and setting up the schema.
    This function sets up the complete database structure for the security camera system.
    """
    Base.metadata.create_all(bind=engine)

# Backwards compatibility alias
def create_tables():
    """Deprecated: Use initialize_database() instead"""
    print("⚠️  Warning: create_tables() is deprecated, use initialize_database() instead")
    initialize_database()
