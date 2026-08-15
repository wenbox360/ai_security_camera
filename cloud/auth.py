from datetime import datetime, timedelta, timezone
import hashlib
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from typing import Optional

from .config import settings
from .database import Device, User

# PBKDF2-SHA256 avoids fixed input-length limits and stores only salted hashes.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (TypeError, ValueError):
        return False


def get_password_hash(password: str) -> str:
    """Hash a password"""
    return pwd_context.hash(password)


def get_device_api_key_hash(api_key: str) -> str:
    """Create a lookup-safe digest for a high-entropy generated credential."""
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_token(token: str, db: Session) -> Optional[User]:
    """Verify a JWT token and return the user"""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            return None

        user = db.query(User).filter(User.username == username).first()
        return user
    except JWTError:
        return None


def verify_api_key(api_key: str, db: Session) -> Optional[Device]:
    """Verify a Pi device API key"""
    digest = get_device_api_key_hash(api_key)
    device = (
        db.query(Device)
        .filter(Device.is_active.is_(True), Device.api_key_hash == digest)
        .first()
    )
    if device is None:
        return None
    device.last_seen = datetime.now(timezone.utc)
    db.commit()
    return device


def authenticate_user(username: str, password: str, db: Session) -> Optional[User]:
    """Authenticate a user with username and password"""
    user = db.query(User).filter(User.username == username).first()
    if (
        not user
        or not user.is_active
        or not verify_password(password, user.hashed_password)
    ):
        return None
    return user
