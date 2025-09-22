#!/bin/bash

# AI Security Camera - Pi Configuration Script
# This script configures a Pi device to connect to the cloud backend

set -e

echo "🔧 AI Security Camera - Pi Configuration"
echo "========================================"

# Check if cloud config exists
if [ ! -f "cloud/aws-config.json" ]; then
    echo "❌ Cloud configuration not found!"
    echo "Please deploy the cloud infrastructure first with:"
    echo "  cd cloud && ./setup-aws-infrastructure.sh"
    exit 1
fi

# Load cloud configuration
CLOUD_API_URL="http://$(jq -r '.alb_dns' cloud/aws-config.json)"

echo "📋 Cloud Configuration:"
echo "  API URL: $CLOUD_API_URL"
echo ""

# Get device API key
echo "🔑 Device Configuration:"
read -p "Enter device API key from cloud setup: " API_KEY

if [ -z "$API_KEY" ]; then
    echo "❌ API key is required!"
    exit 1
fi

# Create Pi configuration file
echo "📝 Creating Pi configuration..."

cat > pi/config/cloud_config.py << EOF
"""
Cloud configuration for Pi device
Generated automatically by setup script
"""

# Cloud API Configuration
CLOUD_API_URL = "$CLOUD_API_URL"
DEVICE_API_KEY = "$API_KEY"

# Upload settings
MAX_RETRY_ATTEMPTS = 3
RETRY_DELAY = 5  # seconds
UPLOAD_TIMEOUT = 30  # seconds

# Local processing settings (before cloud upload)
CONFIDENCE_THRESHOLD = 0.5
DWELLER_TIME_THRESHOLD = 10  # seconds
UNKNOWN_PERSON_COOLDOWN = 300  # 5 minutes

# Queue settings
MAX_QUEUE_SIZE = 100
QUEUE_FLUSH_INTERVAL = 60  # seconds
EOF

echo "✅ Pi configuration created at: pi/config/cloud_config.py"
echo ""

# Update main Pi configuration to use cloud config
echo "🔄 Updating main Pi configuration..."

# Create or update settings.py to import cloud config
cat > pi/config/settings.py << EOF
"""
Main configuration for AI Security Camera Pi
"""

import os
from datetime import datetime

# Import cloud configuration
from .cloud_config import *

# Camera settings
CAMERA_RESOLUTION = (1920, 1080)
CAMERA_FPS = 30
CAPTURE_DURATION = 10  # seconds for video clips

# PIR sensor settings
PIR_PIN = 18
PIR_SENSITIVITY_DELAY = 2  # seconds

# Face recognition settings
FACE_RECOGNITION_TOLERANCE = 0.6
FACE_MODEL = "hog"  # or "cnn" for better accuracy

# YOLO settings
YOLO_MODEL_PATH = "vision/models/yolov8n.pt"
PERSON_CLASS_ID = 0

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = f"captures/logs/security_{datetime.now().strftime('%Y%m%d')}.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# File paths
CAPTURES_DIR = "captures"
KNOWN_FACES_DIR = "known_faces"
TEMP_DIR = "temp"

# Ensure directories exist
os.makedirs(CAPTURES_DIR, exist_ok=True)
os.makedirs(f"{CAPTURES_DIR}/logs", exist_ok=True)
os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
EOF

echo "✅ Main Pi configuration updated"
echo ""

# Test cloud connection
echo "🔍 Testing cloud connection..."

cd pi

python3 -c "
import sys
sys.path.append('.')
from utils.cloud_communicator import CloudCommunicator
from config.settings import CLOUD_API_URL, DEVICE_API_KEY

print(f'Testing connection to: {CLOUD_API_URL}')

communicator = CloudCommunicator()
if communicator.test_connection():
    print('✅ Cloud connection successful!')
else:
    print('❌ Cloud connection failed!')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Pi configuration complete!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Install Pi dependencies: cd pi && pip install -r requirements.txt"
    echo "2. Set up known faces in: pi/known_faces/"
    echo "3. Run the security system: cd pi && python main.py"
    echo ""
    echo "🔍 Useful commands:"
    echo "  Test PIR sensor: cd pi && python test/pir_test.py"
    echo "  Test camera+YOLO: cd pi && python test/camera_yolo_test.py"
    echo "  View logs: tail -f pi/captures/logs/security_*.log"
else
    echo ""
    echo "❌ Configuration failed - please check your API key and cloud deployment"
fi
