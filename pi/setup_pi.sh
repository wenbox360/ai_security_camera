#!/bin/bash
# setup_pi.sh - Raspberry Pi setup script for AI Security Camera

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
python3 -m venv ~/ai_camera_env
source ~/ai_camera_env/bin/activate

# Upgrade pip
echo "⬆️  Upgrading pip..."
pip install --upgrade pip

# Install Python packages (in order of likelihood to succeed)
echo "📚 Installing Python packages..."

# Install basic dependencies first
pip install numpy>=1.21.0
pip install Pillow>=8.0.0

# Try to install face-recognition (might need cmake)
echo "👤 Installing face recognition..."
if ! pip install face-recognition>=1.3.0; then
    echo "⚠️  face-recognition failed, trying with cmake..."
    sudo apt-get install -y cmake
    pip install face-recognition>=1.3.0
fi

# Install ultralytics (YOLO)
echo "🎯 Installing YOLO (ultralytics)..."
pip install ultralytics>=8.0.0

# Install OpenCV (try pip first, fallback to system)
echo "📹 Installing OpenCV..."
if ! pip install opencv-python>=4.5.0; then
    echo "⚠️  Using system OpenCV instead"
fi

echo "✅ Setup complete!"
echo ""
echo "🚀 To activate the environment:"
echo "   source ~/ai_camera_env/bin/activate"
echo ""
echo "🧪 To test the installation:"
echo "   cd /path/to/your/project"
echo "   python3 test_system.py"
