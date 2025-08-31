"""
Minimal Behavior Analyzer - Focus on frame count issue
"""

import time
import cv2
import numpy as np

class BehaviorAnalyzer:
    """Minimal analyzer focused on frame count debugging"""
    
    def __init__(self):
        """Initialize minimal analyzer"""
        pass
    
    def analyze_video_simple(self, video_file_path):
        """
        Simple video analysis focused on frame counting
        """
        if not video_file_path:
            return {'error': 'No video file provided'}
        
        print(f"🔍 Analyzing video: {video_file_path}")
        
        try:
            cap = cv2.VideoCapture(video_file_path)
            
            if not cap.isOpened():
                return {'error': 'Could not open video file'}
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count_meta = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
            height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
            
            print(f"📊 Video Properties:")
            print(f"   FPS: {fps}")
            print(f"   Frame Count (metadata): {frame_count_meta}")
            print(f"   Resolution: {int(width)}x{int(height)}")
            
            # Check if metadata is reliable
            if frame_count_meta <= 0 or frame_count_meta > 100000:
                print(f"❌ Invalid frame count: {frame_count_meta}, counting manually...")
                
                # Count frames manually
                manual_count = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    manual_count += 1
                
                video_duration = manual_count / fps if fps > 0 else 0
                print(f"✅ Manual count: {manual_count} frames")
                print(f"✅ Duration: {video_duration:.2f}s")
                
                cap.release()
                return {
                    'success': True,
                    'method': 'manual_count',
                    'frame_count': manual_count,
                    'duration': video_duration,
                    'fps': fps,
                    'metadata_frame_count': frame_count_meta
                }
            else:
                # Use metadata
                video_duration = frame_count_meta / fps if fps > 0 else 0
                print(f"✅ Using metadata: {frame_count_meta} frames")
                print(f"✅ Duration: {video_duration:.2f}s")
                
                cap.release()
                return {
                    'success': True,
                    'method': 'metadata',
                    'frame_count': frame_count_meta,
                    'duration': video_duration,
                    'fps': fps,
                    'metadata_frame_count': frame_count_meta
                }
                
        except Exception as e:
            return {'error': f'Analysis failed: {str(e)}'}
        
    def test_video_file(self, video_file):
        """Test a video file and report results"""
        result = self.analyze_video_simple(video_file)
        
        if 'error' in result:
            print(f"❌ Error: {result['error']}")
            return False
        
        print(f"✅ Analysis successful!")
        print(f"   Method: {result['method']}")
        print(f"   Frame count: {result['frame_count']}")
        print(f"   Duration: {result['duration']:.2f}s")
        
        if result['method'] == 'manual_count':
            print(f"   ⚠️  Had to count manually due to bad metadata: {result['metadata_frame_count']}")
        
        return True