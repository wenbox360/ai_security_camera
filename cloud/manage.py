#!/usr/bin/env python3
"""
Management script for AI Security Camera Cloud
"""

import sys
import os
import argparse
import secrets
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import User, Device, Base, get_db_url

def get_session():
    """Get database session"""
    engine = create_engine(get_db_url())
    Session = sessionmaker(bind=engine)
    return Session()

def create_user(username: str, email: str):
    """Create a new user"""
    print(f"Creating user: {username} ({email})")
    
    session = get_session()
    
    try:
        # Check if user exists
        existing_user = session.query(User).filter(
            (User.username == username) | (User.email == email)
        ).first()
        
        if existing_user:
            print(f"❌ User with username '{username}' or email '{email}' already exists")
            return False
        
        # Create user
        user = User(
            username=username,
            email=email,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        session.add(user)
        session.commit()
        
        print(f"✅ User created successfully with ID: {user.id}")
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating user: {e}")
        return False
    finally:
        session.close()

def create_device(user_id: int, device_name: str):
    """Create a new Pi device for a user"""
    print(f"Creating device '{device_name}' for user ID {user_id}")
    
    session = get_session()
    
    try:
        # Check if user exists
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            print(f"❌ User with ID {user_id} not found")
            return False
        
        # Generate API key
        api_key = secrets.token_urlsafe(32)
        
        # Create device
        device = Device(
            user_id=user_id,
            device_name=device_name,
            api_key=api_key,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        session.add(device)
        session.commit()
        
        print(f"✅ Device created successfully!")
        print(f"   Device ID: {device.id}")
        print(f"   Device Name: {device_name}")
        print(f"   API Key: {api_key}")
        print("")
        print("⚠️  IMPORTANT: Save this API key! You'll need it to configure your Pi device.")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error creating device: {e}")
        return False
    finally:
        session.close()

def list_users():
    """List all users"""
    print("📋 Users:")
    
    session = get_session()
    
    try:
        users = session.query(User).all()
        
        if not users:
            print("  No users found")
            return
        
        for user in users:
            status = "✅ Active" if user.is_active else "❌ Inactive"
            print(f"  ID: {user.id} | {user.username} ({user.email}) | {status}")
        
    except Exception as e:
        print(f"❌ Error listing users: {e}")
    finally:
        session.close()

def list_devices():
    """List all devices"""
    print("📋 Devices:")
    
    session = get_session()
    
    try:
        devices = session.query(Device).join(User).all()
        
        if not devices:
            print("  No devices found")
            return
        
        for device in devices:
            status = "✅ Active" if device.is_active else "❌ Inactive"
            print(f"  ID: {device.id} | {device.device_name} | User: {device.user.username} | {status}")
        
    except Exception as e:
        print(f"❌ Error listing devices: {e}")
    finally:
        session.close()

def init_db():
    """Initialize database tables"""
    print("Creating database tables...")
    
    try:
        engine = create_engine(get_db_url())
        Base.metadata.create_all(bind=engine)
        print("✅ Database initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="AI Security Camera Cloud Management")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Init database
    subparsers.add_parser('init-db', help='Initialize database tables')
    
    # User management
    user_parser = subparsers.add_parser('create-user', help='Create a new user')
    user_parser.add_argument('username', help='Username')
    user_parser.add_argument('email', help='Email address')
    
    subparsers.add_parser('list-users', help='List all users')
    
    # Device management
    device_parser = subparsers.add_parser('create-device', help='Create a new Pi device')
    device_parser.add_argument('user_id', type=int, help='User ID who owns the device')
    device_parser.add_argument('device_name', help='Device name')
    
    subparsers.add_parser('list-devices', help='List all devices')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'init-db':
        init_db()
    elif args.command == 'create-user':
        create_user(args.username, args.email)
    elif args.command == 'list-users':
        list_users()
    elif args.command == 'create-device':
        create_device(args.user_id, args.device_name)
    elif args.command == 'list-devices':
        list_devices()

if __name__ == "__main__":
    main()
