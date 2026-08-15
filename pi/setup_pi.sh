#!/usr/bin/env bash
# setup_pi.sh - Raspberry Pi setup script for AI Security Camera

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo "🔧 Setting up Raspberry Pi for AI Security Camera"
echo "================================================"

# Update system
echo "📦 Updating system packages..."
sudo apt-get update

# Install system dependencies
echo "🛠️  Installing system dependencies..."
sudo apt-get install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    cmake \
    pkg-config \
    libcap-dev \
    libopenblas-dev \
    liblapack-dev \
    libx11-dev \
    libgtk-3-dev \
    python3-opencv

# Install GPIO library (system package is more reliable)
echo "📡 Installing GPIO support..."
sudo apt-get install -y python3-rpi.gpio

# Install camera support
echo "📷 Installing camera support..."
sudo apt-get install -y python3-picamera2

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv --system-site-packages "$VENV_DIR"
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install Python packages (in order of likelihood to succeed)
echo "📚 Installing Python packages..."

# Install basic dependencies first
python -m pip install "numpy>=1.21.0" "Pillow>=8.0.0"

# Try to install face-recognition (might need cmake)
echo "👤 Installing face recognition..."
if ! python -m pip install "face-recognition>=1.3.0"; then
    echo "⚠️  face-recognition failed, trying with cmake..."
    sudo apt-get install -y cmake
    python -m pip install "face-recognition>=1.3.0"
fi

# Install ultralytics (YOLO)
echo "🎯 Installing YOLO (ultralytics)..."
python -m pip install "ultralytics>=8.0.0"

# Install OpenCV (try pip first, fallback to system)
echo "📹 Installing OpenCV..."
if ! python -m pip install "opencv-python>=4.5.0"; then
    echo "⚠️  Using system OpenCV instead"
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 To activate the environment:"
echo "   source $VENV_DIR/bin/activate"
echo ""
echo "🧪 To test the installation:"
echo "   cd $SCRIPT_DIR/.."
echo "   python3 -m pi.test.test_system"
