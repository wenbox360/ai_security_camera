import boto3
from botocore.exceptions import ClientError
from typing import Optional
import logging
from datetime import datetime, timedelta
import io

logger = logging.getLogger(__name__)

def upload_to_s3(file_obj, key: str, s3_client, bucket_name: str) -> str:
    """
    Upload a file to S3 and return the S3 URL
    
    Args:
        file_obj: File object to upload
        key: S3 key/path for the file
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        
    Returns:
        S3 URL of the uploaded file
    """
    try:
        # Reset file pointer
        file_obj.seek(0)
        
        # Upload file
        s3_client.upload_fileobj(
            file_obj,
            bucket_name,
            key,
            ExtraArgs={
                'ContentType': 'image/jpeg' if key.endswith('.jpg') else 'video/mp4'
            }
        )
        
        # Return S3 URL
        return f"s3://{bucket_name}/{key}"
        
    except ClientError as e:
        logger.error(f"Failed to upload {key} to S3: {str(e)}")
        raise

def generate_presigned_url(s3_url: str, s3_client, bucket_name: str, expiration: int = 3600) -> Optional[str]:
    """
    Generate a presigned URL for an S3 object
    
    Args:
        s3_url: S3 URL (s3://bucket/key format)
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        expiration: URL expiration time in seconds
        
    Returns:
        Presigned URL or None if error
    """
    try:
        # Extract key from S3 URL
        if not s3_url.startswith('s3://'):
            return s3_url  # Return as-is if not S3 URL
        
        key = s3_url.replace(f's3://{bucket_name}/', '')
        
        # Generate presigned URL
        response = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expiration
        )
        
        return response
        
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for {s3_url}: {str(e)}")
        return None

def delete_from_s3(s3_url: str, s3_client, bucket_name: str) -> bool:
    """
    Delete a file from S3
    
    Args:
        s3_url: S3 URL (s3://bucket/key format)
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract key from S3 URL
        if not s3_url.startswith('s3://'):
            return False
        
        key = s3_url.replace(f's3://{bucket_name}/', '')
        
        # Delete object
        s3_client.delete_object(Bucket=bucket_name, Key=key)
        return True
        
    except ClientError as e:
        logger.error(f"Failed to delete {s3_url} from S3: {str(e)}")
        return False

def list_old_files(s3_client, bucket_name: str, prefix: str, days_old: int) -> list:
    """
    List files older than specified days
    
    Args:
        s3_client: Boto3 S3 client
        bucket_name: S3 bucket name
        prefix: S3 prefix to filter files
        days_old: Number of days old
        
    Returns:
        List of old file keys
    """
    try:
        cutoff_date = datetime.utcnow().replace(tzinfo=None) - timedelta(days=days_old)
        old_files = []
        
        paginator = s3_client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=bucket_name, Prefix=prefix)
        
        for page in pages:
            if 'Contents' in page:
                for obj in page['Contents']:
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        old_files.append(obj['Key'])
        
        return old_files
        
    except ClientError as e:
        logger.error(f"Failed to list old files: {str(e)}")
        return []
