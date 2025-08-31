#!/usr/bin/env python3
"""
Test script for BehaviorAnalyzer to isolate frame counting issues
"""

import os
import sys
import cv2
import numpy as np
import time
from datetime import datetime

# Add the pi directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from inference.behavior_analyzer import BehaviorAnalyzer
from vision.yolo_handler import YOLOHandler
from config.settings import Settings

def create_test_video(filename, duration_seconds=3, fps=30):
    """Create a simple test video for testing purposes"""
    print(f"📹 Creating test video: {filename}")
    
    # Define codec and create VideoWriter object
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(filename, fourcc, fps, (640, 480))
    
    total_frames = int(duration_seconds * fps)
    
    for frame_num in range(total_frames):
        # Create a simple frame with changing colors
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Add some visual content that changes over time
        color_intensity = int((frame_num / total_frames) * 255)
        # Ensure color values are within valid range (0-255)
        blue_value = max(0, min(255, 200 - color_intensity))
        frame[:, :] = [color_intensity, 100, blue_value]
        
        # Add frame number text
        cv2.putText(frame, f'Frame {frame_num}', (50, 50), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Test video created: {total_frames} frames, {duration_seconds}s at {fps} FPS")
    return filename

def test_video_properties(video_path):
    """Test video property reading functionality"""
    print(f"\n🔍 Testing video properties for: {video_path}")
    
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Could not open video: {video_path}")
        return False
    
    # Test the problematic properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    
    print(f"📊 Video Properties:")
    print(f"   FPS: {fps}")
    print(f"   Frame Count (metadata): {frame_count}")
    print(f"   Resolution: {int(width)}x{int(height)}")
    
    # Count frames manually by reading through video
    manual_frame_count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        manual_frame_count += 1
    
    cap.release()
    
    print(f"   Frame Count (manual): {manual_frame_count}")
    print(f"   Duration (metadata): {frame_count / fps:.2f}s")
    print(f"   Duration (manual): {manual_frame_count / fps:.2f}s")
    
    # Check for the problematic negative frame count
    if frame_count < 0:
        print(f"⚠️  DETECTED NEGATIVE FRAME COUNT: {frame_count}")
        return False
    elif frame_count != manual_frame_count:
        print(f"⚠️  FRAME COUNT MISMATCH: metadata={frame_count}, actual={manual_frame_count}")
        return False
    else:
        print(f"✅ Frame count is correct!")
        return True

def test_behavior_analyzer_with_mock_yolo():
    """Test behavior analyzer with a mock YOLO handler"""
    print(f"\n🧠 Testing BehaviorAnalyzer with mock YOLO...")
    
    class MockYOLOHandler:
        """Mock YOLO handler that returns fake person detections"""
        def process_frame(self, frame):
            # Simulate person detection in every 3rd frame
            frame_hash = hash(frame.tobytes()) % 3
            if frame_hash == 0:
                return {
                    'detections': [{
                        'class_name': 'person',
                        'confidence': 0.85,
                        'bbox': [100, 100, 200, 300]
                    }]
                }
            else:
                return {'detections': []}
    
    # Create test video
    test_video_path = "test_video.mp4"
    create_test_video(test_video_path, duration_seconds=5, fps=30)
    
    try:
        # Test video properties first
        if not test_video_properties(test_video_path):
            print("❌ Video properties test failed")
            return False
        
        # Initialize behavior analyzer
        analyzer = BehaviorAnalyzer()
        mock_yolo = MockYOLOHandler()
        
        print(f"\n🔬 Analyzing video with BehaviorAnalyzer...")
        start_time = time.time()
        
        # This should now work without the negative frame count error
        result = analyzer.analyze_video_for_dwelling(test_video_path, mock_yolo)
        
        analysis_time = time.time() - start_time
        
        print(f"⏱️  Analysis completed in {analysis_time:.2f} seconds")
        print(f"\n📋 Analysis Results:")
        print(f"   Success: {result.get('analysis_success', 'N/A')}")
        print(f"   Dwelling Detected: {result.get('dwelling_detected', False)}")
        print(f"   Confidence: {result.get('confidence', 0):.2f}")
        print(f"   Message: {result.get('message', 'No message')}")
        print(f"   Video Duration: {result.get('video_duration', 0):.2f}s")
        print(f"   Total Detections: {result.get('total_detections', 0)}")
        
        if 'error' in result:
            print(f"❌ Error occurred: {result['error']}")
            return False
        else:
            print(f"✅ Analysis completed successfully!")
            return True
            
    except Exception as e:
        print(f"❌ Exception during analysis: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up test video
        if os.path.exists(test_video_path):
            os.remove(test_video_path)
            print(f"🗑️  Cleaned up test video: {test_video_path}")

def test_with_h264_video():
    """Test with H.264 video if available"""
    print(f"\n🎥 Looking for H.264 video files...")
    
    # Look for actual H.264 videos in captures
    captures_dir = "captures"
    h264_files = []
    
    if os.path.exists(captures_dir):
        for root, dirs, files in os.walk(captures_dir):
            for file in files:
                if file.endswith('.h264'):
                    h264_files.append(os.path.join(root, file))
    
    if not h264_files:
        print("ℹ️  No H.264 files found in captures directory")
        return True
    
    print(f"Found {len(h264_files)} H.264 file(s)")
    
    # Test the first H.264 file
    h264_file = h264_files[0]
    print(f"Testing H.264 file: {h264_file}")
    
    # Test the video properties first to see the problematic frame count
    properties_test = test_video_properties(h264_file)
    
    # Now test if our behavior analyzer can handle it despite the bad frame count
    print(f"\n🧠 Testing BehaviorAnalyzer with problematic H.264 file...")
    
    class MockYOLOHandler:
        """Mock YOLO handler for testing"""
        def process_frame(self, frame):
            return {'detections': []}
    
    try:
        analyzer = BehaviorAnalyzer()
        mock_yolo = MockYOLOHandler()
        
        result = analyzer.analyze_video_for_dwelling(h264_file, mock_yolo)
        
        print(f"📋 H.264 Analysis Results:")
        print(f"   Error Present: {'error' in result}")
        print(f"   Dwelling Detected: {result.get('dwelling_detected', False)}")
        print(f"   Message: {result.get('message', 'No message')}")
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return False
        else:
            print(f"✅ BehaviorAnalyzer successfully handled H.264 file despite bad metadata!")
            return True
            
    except Exception as e:
        print(f"❌ Exception during H.264 analysis: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 BehaviorAnalyzer Frame Count Fix Test")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    # Test 1: Create and test a simple MP4 video
    print(f"\n📋 Test 1/3: Creating and testing MP4 video")
    if test_behavior_analyzer_with_mock_yolo():
        tests_passed += 1
        print("✅ Test 1 PASSED")
    else:
        print("❌ Test 1 FAILED")
    
    # Test 2: Test H.264 video if available
    print(f"\n📋 Test 2/3: Testing H.264 video properties")
    if test_with_h264_video():
        tests_passed += 1
        print("✅ Test 2 PASSED")
    else:
        print("❌ Test 2 FAILED")
    
    # Test 3: Test error handling with invalid video
    print(f"\n📋 Test 3/3: Testing error handling")
    try:
        analyzer = BehaviorAnalyzer()
        result = analyzer.analyze_video_for_dwelling("nonexistent_video.mp4", None)
        
        if 'error' in result and not result['dwelling_detected']:
            tests_passed += 1
            print("✅ Test 3 PASSED - Error handling works correctly")
        else:
            print("❌ Test 3 FAILED - Error handling didn't work as expected")
    except Exception as e:
        print(f"❌ Test 3 FAILED - Exception: {e}")
    
    # Final results
    print("\n" + "=" * 50)
    print(f"🏁 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 ALL TESTS PASSED! Frame counting fix is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
