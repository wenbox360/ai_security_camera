#!/usr/bin/env python3
"""
Cloud Configuration Setup Script
Helps configure the Pi device for cloud communication
"""

import os
import sys
import json
import uuid
from typing import Dict, Any

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.settings import Settings
from utils.cloud_communicator import CloudCommunicator

def generate_device_id() -> str:
    """Generate a unique device ID"""
    return f"pi_{uuid.uuid4().hex[:8]}"

def test_cloud_connection(api_url: str, device_id: str, api_key: str) -> bool:
    """Test connection to cloud API"""
    try:
        communicator = CloudCommunicator(api_url, device_id, api_key)
        return communicator.test_connection()
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def create_config_file(config: Dict[str, Any]) -> bool:
    """Create or update cloud configuration file"""
    try:
        config_file = "config/cloud_config.json"
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        print(f"✅ Configuration saved to: {config_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to save configuration: {e}")
        return False

def update_settings_file(api_url: str, device_id: str, api_key: str) -> bool:
    """Update the settings.py file with cloud configuration"""
    try:
        settings_file = "config/settings.py"
        
        # Read current settings
        with open(settings_file, 'r') as f:
            content = f.read()
        
        # Update cloud settings
        lines = content.split('\n')
        updated_lines = []
        
        for line in lines:
            if line.strip().startswith('CLOUD_API_URL ='):
                updated_lines.append(f'CLOUD_API_URL = "{api_url}"')
            elif line.strip().startswith('DEVICE_ID ='):
                updated_lines.append(f'DEVICE_ID = "{device_id}"')
            elif line.strip().startswith('DEVICE_API_KEY ='):
                updated_lines.append(f'DEVICE_API_KEY = "{api_key}"')
            else:
                updated_lines.append(line)
        
        # Write updated settings
        with open(settings_file, 'w') as f:
            f.write('\n'.join(updated_lines))
        
        print(f"✅ Settings updated in: {settings_file}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to update settings: {e}")
        return False

def main():
    """Main configuration setup"""
    print("🌐 AI Security Camera - Cloud Configuration Setup")
    print("=" * 50)
    
    # Get current configuration
    cloud_config = Settings.get_cloud_config()
    
    print(f"Current configuration:")
    print(f"  API URL: {cloud_config['api_url']}")
    print(f"  Device ID: {cloud_config['device_id']}")
    print(f"  API Key: {'***' + cloud_config['api_key'][-4:] if cloud_config['api_key'] else 'Not set'}")
    print()
    
    # Prompt for new configuration
    print("Enter new configuration (press Enter to keep current values):")
    
    # API URL
    api_url = input(f"Cloud API URL [{cloud_config['api_url']}]: ").strip()
    if not api_url:
        api_url = cloud_config['api_url']
    
    # Device ID
    current_device_id = cloud_config['device_id'] or generate_device_id()
    device_id = input(f"Device ID [{current_device_id}]: ").strip()
    if not device_id:
        device_id = current_device_id
    
    # API Key
    api_key = input("Device API Key: ").strip()
    if not api_key:
        api_key = cloud_config['api_key']
    
    if not api_key:
        print("❌ API key is required for cloud communication")
        print("Please get your device API key from the cloud management system:")
        print("  python cloud/manage.py create-device <user_id> <device_name>")
        return
    
    print(f"\n📋 Configuration Summary:")
    print(f"  API URL: {api_url}")
    print(f"  Device ID: {device_id}")
    print(f"  API Key: ***{api_key[-4:]}")
    print()
    
    # Confirm
    confirm = input("Apply this configuration? (y/N): ").strip().lower()
    if confirm != 'y':
        print("Configuration cancelled")
        return
    
    # Test connection
    print("🔍 Testing cloud connection...")
    if test_cloud_connection(api_url, device_id, api_key):
        print("✅ Cloud connection successful!")
        
        # Update settings file
        if update_settings_file(api_url, device_id, api_key):
            print("✅ Configuration complete!")
            print("\nNext steps:")
            print("1. Restart the security camera system")
            print("2. Check logs for cloud communication status")
            print("3. Test event sending by triggering motion detection")
        else:
            print("❌ Failed to update settings file")
    else:
        print("❌ Cloud connection failed!")
        print("Please check:")
        print("1. Cloud API URL is correct and accessible")
        print("2. Device API key is valid")
        print("3. Network connectivity")
        print("4. Cloud service is running")

if __name__ == "__main__":
    main()
