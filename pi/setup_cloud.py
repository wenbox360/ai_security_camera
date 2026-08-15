#!/usr/bin/env python3
"""
Cloud Configuration Setup Script
Helps configure the Pi device for cloud communication
"""

import argparse
import getpass
import uuid
from pathlib import Path

from .config.settings import Settings
from .utils.cloud_communicator import CloudCommunicator


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


def write_env_file(api_url: str, device_id: str, api_key: str) -> bool:
    """Write private device configuration to the ignored Pi environment file."""
    try:
        env_file = Path(__file__).resolve().parent / ".env"
        env_file.write_text(
            f"CLOUD_API_URL={api_url}\n"
            f"DEVICE_ID={device_id}\n"
            f"DEVICE_API_KEY={api_key}\n"
        )
        env_file.chmod(0o600)
        print(f"✅ Private configuration saved to: {env_file}")
        return True
    except Exception as e:
        print(f"❌ Failed to write private configuration: {e}")
        return False


def main():
    """Main configuration setup"""
    parser = argparse.ArgumentParser(description="Configure Pi cloud connectivity")
    parser.add_argument(
        "--test", action="store_true", help="test the current environment configuration"
    )
    args = parser.parse_args()

    if args.test:
        config = Settings.get_cloud_config()
        if not config["api_key"]:
            raise SystemExit("DEVICE_API_KEY is not configured in pi/.env")
        raise SystemExit(
            0
            if test_cloud_connection(
                config["api_url"], config["device_id"], config["api_key"]
            )
            else 1
        )

    print("🌐 AI Security Camera - Cloud Configuration Setup")
    print("=" * 50)

    # Get current configuration
    cloud_config = Settings.get_cloud_config()

    print("Current configuration:")
    print(f"  API URL: {cloud_config['api_url']}")
    print(f"  Device ID: {cloud_config['device_id']}")
    print(
        f"  API Key: {'***' + cloud_config['api_key'][-4:] if cloud_config['api_key'] else 'Not set'}"
    )
    print()

    # Prompt for new configuration
    print("Enter new configuration (press Enter to keep current values):")

    # API URL
    api_url = input(f"Cloud API URL [{cloud_config['api_url']}]: ").strip()
    if not api_url:
        api_url = cloud_config["api_url"]

    # Device ID
    current_device_id = cloud_config["device_id"] or generate_device_id()
    device_id = input(f"Device ID [{current_device_id}]: ").strip()
    if not device_id:
        device_id = current_device_id

    # API Key
    api_key = getpass.getpass("Device API Key: ").strip()
    if not api_key:
        api_key = cloud_config["api_key"]

    if not api_key:
        print("❌ API key is required for cloud communication")
        print("Please get your device API key from the cloud management system:")
        print("  python cloud/manage.py create-device <user_id> <device_name>")
        return

    print("\n📋 Configuration Summary:")
    print(f"  API URL: {api_url}")
    print(f"  Device ID: {device_id}")
    print(f"  API Key: ***{api_key[-4:]}")
    print()

    # Confirm
    confirm = input("Apply this configuration? (y/N): ").strip().lower()
    if confirm != "y":
        print("Configuration cancelled")
        return

    # Test connection
    print("🔍 Testing cloud connection...")
    if test_cloud_connection(api_url, device_id, api_key):
        print("✅ Cloud connection successful!")

        if write_env_file(api_url, device_id, api_key):
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
