#!/usr/bin/env python3
"""
MINIMAL behavior analyzer test to isolate frame count issue
"""

import cv2
import os

def test_frame_count_issue():
    """Test frame count reading with minimal code"""
    print("🔍 MINIMAL Frame Count Test")
    print("=" * 30)
    
    # Test files if they exist
    test_files = [
        "captures/videos/test_video_20250831_190928.h264",
        "test_minimal_20250831_*.h264",
        "test_minimal_20250831_*.mp4"
    ]
    
    # Find existing files
    import glob
    existing_files = []
    for pattern in test_files:
        existing_files.extend(glob.glob(pattern))
    
    if not existing_files:
        print("❌ No test video files found")
        return
    
    for video_file in existing_files[:3]:  # Test max 3 files
        print(f"\n📹 Testing: {video_file}")
        
        if not os.path.exists(video_file):
            print("   ❌ File doesn't exist")
            continue
            
        file_size = os.path.getsize(video_file)
        print(f"   📊 Size: {file_size} bytes")
        
        # Test with OpenCV
        cap = cv2.VideoCapture(video_file)
        
        if not cap.isOpened():
            print("   ❌ Cannot open with OpenCV")
            continue
        
        # Get metadata
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        
        print(f"   📊 Metadata:")
        print(f"      FPS: {fps}")
        print(f"      Frame Count: {frame_count_meta}")
        print(f"      Resolution: {int(width)}x{int(height)}")
        
        # Manual count
        print("   🔢 Counting frames manually...")
        manual_count = 0
        error_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            manual_count += 1
            
            # Check for decode errors (frame would be None or corrupted)
            if frame is None:
                error_count += 1
        
        cap.release()
        
        print(f"   📊 Manual count: {manual_count}")
        print(f"   ⚠️  Decode errors: {error_count}")
        
        # Analysis
        if frame_count_meta == manual_count and frame_count_meta > 0:
            print("   ✅ METADATA IS CORRECT!")
        elif frame_count_meta < 0:
            print("   ❌ NEGATIVE METADATA (classic H.264 issue)")
        elif manual_count > 0:
            print("   ⚠️  METADATA MISMATCH but video is readable")
        else:
            print("   ❌ COMPLETELY CORRUPTED")
        
        # Expected vs actual
        expected_frames = int(fps * 2) if fps > 0 else 60  # 2 second video
        if abs(manual_count - expected_frames) <= 5:  # Allow 5 frame tolerance
            print(f"   ✅ Frame count reasonable for 2s video (~{expected_frames})")
        else:
            print(f"   ⚠️  Unexpected frame count (expected ~{expected_frames})")

def test_simple_behavior_analyzer():
    """Test the core behavior analyzer logic with minimal code"""
    print(f"\n🧠 MINIMAL Behavior Analyzer Test")
    print("=" * 35)
    
    # Find a test video
    import glob
    video_files = glob.glob("*.h264") + glob.glob("*.mp4")
    
    if not video_files:
        print("❌ No video files to test")
        return
    
    video_file = video_files[0]
    print(f"📹 Testing: {video_file}")
    
    # Minimal behavior analyzer logic
    cap = cv2.VideoCapture(video_file)
    
    if not cap.isOpened():
        print("❌ Cannot open video")
        return
    
    # Get properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    print(f"📊 FPS: {fps}")
    print(f"📊 Metadata frame count: {frame_count_meta}")
    
    # Check if we need to count manually
    if frame_count_meta <= 0 or frame_count_meta > 100000:
        print("⚠️  Bad metadata, counting manually...")
        
        manual_count = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            manual_count += 1
        
        actual_duration = manual_count / fps if fps > 0 else 0
        print(f"✅ Manual count: {manual_count} frames")
        print(f"✅ Actual duration: {actual_duration:.2f}s")
        
    else:
        print(f"✅ Using metadata: {frame_count_meta} frames")
        duration = frame_count_meta / fps if fps > 0 else 0
        print(f"✅ Duration: {duration:.2f}s")
    
    cap.release()

if __name__ == "__main__":
    test_frame_count_issue()
    test_simple_behavior_analyzer()
    print("\n🏁 Minimal tests complete!")
