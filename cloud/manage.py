#!/usr/bin/env python3
"""Small, import-safe management CLI for the cloud service."""

import argparse
import getpass
import secrets

from .auth import get_device_api_key_hash, get_password_hash
from .database import Base, Device, SessionLocal, User, engine


def get_session():
    return SessionLocal()


def create_user(username: str, email: str, password: str) -> bool:
    session = get_session()
    try:
        if (
            session.query(User)
            .filter((User.username == username) | (User.email == email))
            .first()
        ):
            print("User with that username or email already exists")
            return False
        session.add(
            User(
                username=username,
                email=email,
                hashed_password=get_password_hash(password),
                is_active=True,
            )
        )
        session.commit()
        print(f"Created user {username}")
        return True
    except Exception as exc:
        session.rollback()
        print(f"Unable to create user: {exc}")
        return False
    finally:
        session.close()


def create_device(user_id: int, name: str, device_id: str | None = None) -> bool:
    """Create a device and print its plaintext key exactly once."""
    session = get_session()
    try:
        if session.get(User, user_id) is None:
            print(f"User {user_id} was not found")
            return False
        device_id = device_id or f"device-{secrets.token_hex(8)}"
        if session.query(Device).filter(Device.device_id == device_id).first():
            print(f"Device ID {device_id} already exists")
            return False
        api_key = secrets.token_urlsafe(32)
        session.add(
            Device(
                device_id=device_id,
                name=name,
                owner_id=user_id,
                api_key_hash=get_device_api_key_hash(api_key),
                is_active=True,
            )
        )
        session.commit()
        print(
            f"Created device {device_id}. Save this API key now; it cannot be recovered:\n{api_key}"
        )
        return True
    except Exception as exc:
        session.rollback()
        print(f"Unable to create device: {exc}")
        return False
    finally:
        session.close()


def list_users():
    session = get_session()
    try:
        for user in session.query(User).order_by(User.id):
            print(
                f"{user.id}\t{user.username}\t{user.email}\t{'active' if user.is_active else 'inactive'}"
            )
    finally:
        session.close()


def list_devices():
    session = get_session()
    try:
        for device in session.query(Device).order_by(Device.id):
            print(
                f"{device.id}\t{device.device_id}\t{device.name}\towner={device.owner_id}\t{'active' if device.is_active else 'inactive'}"
            )
    finally:
        session.close()


def init_db() -> bool:
    try:
        Base.metadata.create_all(bind=engine)
        print("Database initialized")
        return True
    except Exception as exc:
        print(f"Unable to initialize database: {exc}")
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="AI Security Camera Cloud Management")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db")
    user = commands.add_parser("create-user")
    user.add_argument("username")
    user.add_argument("email")
    user.add_argument("--password", help="Password to hash; omit to enter it securely")
    commands.add_parser("list-users")
    device = commands.add_parser("create-device")
    device.add_argument("user_id", type=int)
    device.add_argument("name")
    device.add_argument("--device-id")
    commands.add_parser("list-devices")
    args = parser.parse_args()
    if args.command == "init-db":
        return 0 if init_db() else 1
    if args.command == "create-user":
        password = args.password or getpass.getpass("Password: ")
        if not password:
            print("Password cannot be empty")
            return 1
        return 0 if create_user(args.username, args.email, password) else 1
    if args.command == "create-device":
        return 0 if create_device(args.user_id, args.name, args.device_id) else 1
    if args.command == "list-users":
        list_users()
    elif args.command == "list-devices":
        list_devices()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
