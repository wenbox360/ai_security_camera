import logging
from datetime import datetime, timedelta
from typing import Dict, Any

from sqlalchemy.orm import Session
import boto3

from ..celery_app import celery_app
from ..database import get_db, SecurityEvent
from ..config import settings
from ..storage import list_old_files, delete_from_s3

logger = logging.getLogger(__name__)

@celery_app.task
def cleanup_old_files() -> Dict[str, Any]:
    """
    Clean up old files from S3 and database records based on retention policy
    """
    try:
        # Get database session
        db = next(get_db())
        
        # Create S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=settings.file_retention_days)
        
        # Get old events from database
        old_events = db.query(SecurityEvent).filter(
            SecurityEvent.created_at < cutoff_date
        ).all()
        
        deleted_files = 0
        deleted_events = 0
        
        for event in old_events:
            try:
                # Delete files from S3
                if event.image_url:
                    delete_from_s3(event.image_url, s3_client, settings.s3_bucket_name)
                    deleted_files += 1
                
                if event.video_url:
                    delete_from_s3(event.video_url, s3_client, settings.s3_bucket_name)
                    deleted_files += 1
                
                # Delete event from database
                db.delete(event)
                deleted_events += 1
                
            except Exception as e:
                logger.error(f"Error deleting event {event.event_id}: {str(e)}")
                continue
        
        db.commit()
        
        result = {
            "deleted_files": deleted_files,
            "deleted_events": deleted_events,
            "cutoff_date": cutoff_date.isoformat(),
            "status": "completed"
        }
        
        logger.info(f"Cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error during cleanup: {str(e)}")
        raise
    
    finally:
        db.close()

@celery_app.task
def cleanup_failed_uploads() -> Dict[str, Any]:
    """
    Clean up orphaned files in S3 that don't have corresponding database entries
    """
    try:
        db = next(get_db())
        
        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.aws_access_key_id,
            aws_secret_access_key=settings.aws_secret_access_key,
            region_name=settings.aws_region
        )
        
        # Get all files from S3 events folder
        old_files = list_old_files(s3_client, settings.s3_bucket_name, "events/", 1)  # Files older than 1 day
        
        deleted_count = 0
        
        for file_key in old_files:
            # Extract event_id from file path (events/{event_id}/...)
            try:
                event_id = file_key.split('/')[1]
                
                # Check if event exists in database
                event_exists = db.query(SecurityEvent).filter(
                    SecurityEvent.event_id == event_id
                ).first()
                
                if not event_exists:
                    # Delete orphaned file
                    s3_url = f"s3://{settings.s3_bucket_name}/{file_key}"
                    if delete_from_s3(s3_url, s3_client, settings.s3_bucket_name):
                        deleted_count += 1
                        logger.info(f"Deleted orphaned file: {file_key}")
                
            except (IndexError, Exception) as e:
                logger.error(f"Error processing file {file_key}: {str(e)}")
                continue
        
        result = {
            "deleted_orphaned_files": deleted_count,
            "status": "completed"
        }
        
        logger.info(f"Orphaned file cleanup completed: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Error during orphaned file cleanup: {str(e)}")
        raise
    
    finally:
        db.close()
