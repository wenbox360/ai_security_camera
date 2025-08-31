#!/usr/bin/env python3
"""
Test script to create a new H.264 video with improved camera settings
"""

import os
import sys
import time
from datetime import datetime

# Add the pi directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from camera.camera_utils import CameraManager

def test_new_video_recording():
    """Test recording a new video with improved settings"""
    print("🎥 Testing new H.264 recording with improved camera settings...")
    
    try:
        # Initialize camera manager
        camera = CameraManager()
        
        if not camera.setup():
            print("❌ Camera setup failed")
            return None
        
        print("✅ Camera initialized successfully")
        
        # Record a test video
        print("🔴 Recording test video...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        test_filename = f"captures/videos/test_video_{timestamp}.h264"
        
        video_file = camera.record_low_res_video(test_filename)
        
        if video_file:
            print(f"✅ Test video created: {video_file}")
            
            # Check file size
            file_size = os.path.getsize(video_file)
            print(f"📊 File size: {file_size} bytes")
            
            return video_file
        else:
            print("❌ Video recording failed")
            return None
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return None
    finally:
        try:
            camera.cleanup()
        except:
            pass

if __name__ == "__main__":
    print("🧪 Testing Camera Recording Improvements")
    print("=" * 50)
    
    new_video = test_new_video_recording()
    
    if new_video:
        print(f"\n✅ SUCCESS: New video created at {new_video}")
        print("Now test this new file with your behavior analyzer to see if the H.264 corruption is fixed!")
        
        # Test the new video immediately
        print("\n🔍 Testing new video properties...")
        
        import cv2
        cap = cv2.VideoCapture(new_video)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            print(f"📊 New Video Properties:")
            print(f"   FPS: {fps}")
            print(f"   Frame Count: {frame_count}")
            
            if frame_count > 0 and frame_count < 1000:
                print("✅ Frame count looks reasonable!")
            else:
                print(f"⚠️  Frame count still looks suspicious: {frame_count}")
                
            cap.release()
        else:
            print("❌ Could not open new video file")
    else:
        print("\n❌ FAILED: Could not create test video")
