#!/usr/bin/env python3
"""
MINIMAL camera test to isolate H.264 frame count issue
"""

import time
import cv2
import os
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

def test_minimal_recording():
    """Absolute minimal recording test"""
    print("🎥 MINIMAL H.264 Recording Test")
    print("=" * 40)
    
    # Initialize camera with minimal config
    picam2 = Picamera2()
    
    # Simple video config
    video_config = picam2.create_video_configuration(
        main={"format": "RGB888", "size": (640, 480)}
    )
    
    try:
        # Setup camera
        picam2.configure(video_config)
        picam2.start()
        time.sleep(2)  # Let camera stabilize
        
        # Create simple filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Test both formats
        for fmt in ["h264", "mp4"]:
            filename = f"test_minimal_{timestamp}.{fmt}"
            print(f"\n🔴 Recording {fmt.upper()} file...")
            
            try:
                # Simple encoder
                encoder = H264Encoder(bitrate=1000000)
                
                # Record
                picam2.start_recording(encoder, filename)
                time.sleep(2)  # Record for 2 seconds
                picam2.stop_recording()
                
                print(f"✅ Created: {filename}")
                
                # Check file
                if os.path.exists(filename):
                    file_size = os.path.getsize(filename)
                    print(f"📊 File size: {file_size} bytes")
                    
                    # Test with OpenCV
                    print("🔍 Testing with OpenCV...")
                    cap = cv2.VideoCapture(filename)
                    
                    if cap.isOpened():
                        fps = cap.get(cv2.CAP_PROP_FPS)
                        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                        
                        print(f"   FPS: {fps}")
                        print(f"   Frame Count: {frame_count}")
                        print(f"   Resolution: {int(width)}x{int(height)}")
                        
                        # Manual frame count
                        manual_count = 0
                        while True:
                            ret, frame = cap.read()
                            if not ret:
                                break
                            manual_count += 1
                        
                        print(f"   Manual Count: {manual_count}")
                        
                        if frame_count == manual_count and frame_count > 0:
                            print(f"✅ {fmt.upper()}: Frame count is CORRECT!")
                        else:
                            print(f"❌ {fmt.upper()}: Frame count MISMATCH!")
                            
                        cap.release()
                    else:
                        print(f"❌ Could not open {filename}")
                else:
                    print(f"❌ File not created: {filename}")
                    
            except Exception as e:
                print(f"❌ Recording {fmt} failed: {e}")
                try:
                    picam2.stop_recording()
                except:
                    pass
        
    except Exception as e:
        print(f"❌ Camera setup failed: {e}")
    finally:
        try:
            picam2.close()
        except:
            pass

def test_opencv_formats():
    """Test OpenCV with different video formats"""
    print("\n🧪 Testing OpenCV format compatibility...")
    
    # Create a simple test video with OpenCV
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter('opencv_test.mp4', fourcc, 30.0, (640, 480))
    
    # Write 60 frames (2 seconds at 30 FPS)
    for i in range(60):
        frame = cv2.imread('captures/snapshots/snapshot_20250831_184343.jpg') if os.path.exists('captures/snapshots/snapshot_20250831_184343.jpg') else None
        if frame is None:
            # Create a simple frame
            import numpy as np
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            frame[:, :] = [i*4, 100, 200]
        
        frame = cv2.resize(frame, (640, 480))
        out.write(frame)
    
    out.release()
    
    # Test the OpenCV-created video
    cap = cv2.VideoCapture('opencv_test.mp4')
    if cap.isOpened():
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        print(f"📊 OpenCV-created MP4:")
        print(f"   FPS: {fps}")
        print(f"   Frame Count: {frame_count}")
        
        if frame_count == 60:
            print("✅ OpenCV MP4 has correct frame count!")
        else:
            print("❌ Even OpenCV MP4 has wrong frame count!")
        
        cap.release()
    
    # Clean up
    if os.path.exists('opencv_test.mp4'):
        os.remove('opencv_test.mp4')

if __name__ == "__main__":
    test_minimal_recording()
    test_opencv_formats()
    print("\n🏁 Minimal test complete!")
