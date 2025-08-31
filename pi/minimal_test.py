#!/usr/bin/env python3
"""
MINIMAL test script - stripped down to focus on frame count issue
"""

import os
import sys

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from camera.camera_utils import CameraManager
from inference.behavior_analyzer import BehaviorAnalyzer

def minimal_test():
    """Absolute minimal test"""
    print("🧪 MINIMAL Frame Count Test")
    print("=" * 40)
    
    # Test 1: Record a simple video
    print("\n1️⃣  Recording minimal video...")
    camera = CameraManager()
    
    try:
        if camera.setup():
            video_file = camera.record_video_simple()
            if video_file:
                print(f"✅ Video created: {video_file}")
                
                # Test 2: Analyze the video
                print("\n2️⃣  Testing frame count...")
                analyzer = BehaviorAnalyzer()
                result = analyzer.test_video_file(video_file)
                
                if result:
                    print("✅ Frame count test PASSED")
                else:
                    print("❌ Frame count test FAILED")
            else:
                print("❌ Video creation failed")
        else:
            print("❌ Camera setup failed")
    finally:
        camera.cleanup()

if __name__ == "__main__":
    minimal_test()
