"""
Behavior Analyzer for Smart Detection
Video-based analyzer focused on people dwelling detection
"""

import time
import cv2
import numpy as np
from datetime import datetime
from collections import deque
from config.settings import Settings

class BehaviorAnalyzer:
    """Analyzes video footage to identify people dwelling/loitering"""
    
    def __init__(self):
        """Initialize behavior analyzer"""
        # Detection history storage for dwelling analysis
        self.video_analysis_history = deque(maxlen=20)  # Store last 20 video analyses
        self.current_analysis = None
        
        # Dwelling thresholds from settings
        self.dwelling_threshold = Settings.get_loitering_threshold()  # seconds
        
        # Video analysis settings
        self.frame_skip = Settings.get_video_frame_skip()  # Analyze every nth frame for efficiency
        self.min_confidence = Settings.get_min_person_confidence()  # Minimum YOLO confidence for person detection
        
    def analyze_video_for_dwelling(self, video_file_path, yolo_handler):
        """
        Analyze video file for people dwelling patterns
        
        Args:
            video_file_path: Path to the video file to analyze
            yolo_handler: YOLOHandler instance for object detection
            
        Returns:
            dict: Dwelling analysis results
        """
        if not video_file_path:
            return {
                'dwelling_detected': False,
                'confidence': 0,
                'message': 'No video file provided',
                'error': 'Invalid video path'
            }
        
        try:
            # Analyze video for dwelling behavior
            analysis_result = self._analyze_video_file(video_file_path, yolo_handler)
            
            # Store analysis in history
            self.video_analysis_history.append({
                'timestamp': time.time(),
                'video_file': video_file_path,
                'analysis': analysis_result
            })
            
            return analysis_result
            
        except Exception as e:
            return {
                'dwelling_detected': False,
                'confidence': 0,
                'message': f'Video analysis failed: {str(e)}',
                'error': str(e)
            }
    
    def _analyze_video_file(self, video_path, yolo_handler):
        """Analyze video file for dwelling patterns with improved error handling"""
        try:
            import cv2
            import numpy as np
        except ImportError:
            return self._create_error_result('OpenCV not available for video analysis', 'Missing cv2 dependency')
        
        # Wait a moment for file to be fully written
        time.sleep(0.5)
        
        # Open video file
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return self._create_error_result('Could not open video file', 'Video file access failed')
        
        try:
            # Get video properties with validation
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            # Validate video properties
            if fps <= 0 or fps > 120:  # Reasonable FPS range
                print(f"❌ Invalid FPS: {fps}, using default 30")
                fps = 30.0
                
            if total_frames <= 0:
                print(f"❌ Invalid frame count: {total_frames}")
                cap.release()
                return self._create_error_result('Invalid video frame count', 'Corrupt video file')
                
            if total_frames > 100000:  # Sanity check for very long videos
                print(f"⚠️  Very large frame count: {total_frames}, limiting analysis")
                total_frames = min(total_frames, 1800)  # Limit to ~1 minute at 30fps
                
            video_duration = total_frames / fps
            
            # Additional validation
            if video_duration <= 0:
                print(f"❌ Invalid video duration: {video_duration}s")
                cap.release()
                return self._create_error_result('Invalid video duration', 'Duration calculation failed')
                
            if video_duration > 3600:  # Max 1 hour
                print(f"⚠️  Very long video: {video_duration}s, limiting analysis")
                video_duration = min(video_duration, 60.0)  # Limit analysis to 1 minute
                
            print(f"Analyzing video: {video_path}")
            print(f"Duration: {video_duration:.1f}s, FPS: {fps:.1f}, Frames: {total_frames}")
        
        except Exception as e:
            print(f"❌ Error reading video properties: {e}")
            cap.release()
            return self._create_error_result(f'Error reading video properties: {str(e)}', str(e))
        
        # Analysis data
        person_detections = []
        frame_count = 0
        frames_with_people = 0
        total_people_detected = 0
        
        # Analyze frames
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            
            # Skip frames for efficiency (analyze every nth frame)
            if frame_count % self.frame_skip != 0:
                continue
            
            # Run YOLO detection on frame
            yolo_result = yolo_handler.process_frame(frame)
            
            # Count people in this frame
            people_in_frame = [d for d in yolo_result['detections'] 
                             if d['class_name'] == 'person' and d['confidence'] >= self.min_confidence]
            
            if people_in_frame:
                frames_with_people += 1
                total_people_detected += len(people_in_frame)
                
                # Store detection data
                frame_time = frame_count / fps
                person_detections.append({
                    'frame': frame_count,
                    'time': frame_time,
                    'people_count': len(people_in_frame),
                    'people_data': people_in_frame
                })
        
        cap.release()
        
        # Analyze dwelling patterns
        dwelling_analysis = self._analyze_dwelling_patterns(
            person_detections, video_duration, frames_with_people, frame_count // self.frame_skip
        )
        
        return dwelling_analysis
    
    def _analyze_dwelling_patterns(self, person_detections, video_duration, frames_with_people, total_analyzed_frames):
        """Analyze person detection patterns for dwelling behavior"""
        
        if not person_detections:
            return {
                'dwelling_detected': False,
                'confidence': 0,
                'video_duration': video_duration,
                'people_presence_time': 0,
                'message': 'No people detected in video'
            }
        
        # Calculate presence statistics
        people_presence_time = len(person_detections) * self.frame_skip / 30  # Estimate based on frame analysis
        presence_percentage = (frames_with_people / total_analyzed_frames) * 100 if total_analyzed_frames > 0 else 0
        
        # Analyze continuity of presence
        continuous_presence_periods = self._find_continuous_periods(person_detections)
        longest_presence = max(continuous_presence_periods) if continuous_presence_periods else 0
        
        # Determine if dwelling behavior detected
        dwelling_detected = False
        dwelling_confidence = 0
        
        # Dwelling criteria:
        # 1. People present for significant portion of video (>70%)
        # 2. Longest continuous presence exceeds threshold
        # 3. Multiple detection points throughout video
        
        criteria_met = 0
        dwelling_indicators = []
        
        # Criterion 1: High presence percentage
        if presence_percentage >= 70:
            criteria_met += 1
            dwelling_indicators.append(f'high presence ({presence_percentage:.1f}%)')
            dwelling_confidence += 0.4
        
        # Criterion 2: Long continuous presence
        if longest_presence >= self.dwelling_threshold:
            criteria_met += 1
            dwelling_indicators.append(f'continuous presence ({longest_presence:.1f}s)')
            dwelling_confidence += 0.4
        
        # Criterion 3: Consistent detections throughout video
        if len(person_detections) >= 5 and video_duration >= 2:
            detection_spread = self._calculate_detection_spread(person_detections, video_duration)
            if detection_spread >= 0.6:  # Detections spread across 60% of video
                criteria_met += 1
                dwelling_indicators.append('consistent throughout video')
                dwelling_confidence += 0.2
        
        # Dwelling detected if at least 2 criteria met
        dwelling_detected = criteria_met >= 2
        
        # Calculate average people count
        avg_people_count = sum(d['people_count'] for d in person_detections) / len(person_detections)
        
        return {
            'dwelling_detected': dwelling_detected,
            'confidence': min(dwelling_confidence, 1.0),
            'video_duration': video_duration,
            'people_presence_time': people_presence_time,
            'presence_percentage': round(presence_percentage, 1),
            'longest_continuous_presence': longest_presence,
            'average_people_count': round(avg_people_count, 1),
            'criteria_met': criteria_met,
            'dwelling_indicators': dwelling_indicators,
            'total_detections': len(person_detections),
            'message': self._generate_dwelling_message(dwelling_detected, longest_presence, presence_percentage, avg_people_count)
        }
    
    def _find_continuous_periods(self, detections):
        """Find periods of continuous person presence"""
        if not detections:
            return []
        
        periods = []
        current_start = detections[0]['time']
        last_time = current_start
        
        for i in range(1, len(detections)):
            current_time = detections[i]['time']
            time_gap = current_time - last_time
            
            # If gap is too large (>3 seconds), end current period
            if time_gap > 3.0:
                period_duration = last_time - current_start
                periods.append(period_duration)
                current_start = current_time
            
            last_time = current_time
        
        # Add final period
        final_duration = last_time - current_start
        periods.append(final_duration)
        
        return periods
    
    def _calculate_detection_spread(self, detections, video_duration):
        """Calculate how spread out detections are across the video"""
        if not detections or video_duration <= 0:
            return 0
        
        detection_times = [d['time'] for d in detections]
        time_span = max(detection_times) - min(detection_times)
        
        return time_span / video_duration
    
    def _generate_dwelling_message(self, detected, longest_presence, presence_percentage, avg_people):
        """Generate human-readable dwelling message"""
        if detected:
            return f"Dwelling detected: {avg_people:.1f} person(s) present {presence_percentage:.1f}% of video (max continuous: {longest_presence:.1f}s)"
        else:
            if longest_presence > 0:
                return f"Brief presence: {avg_people:.1f} person(s) for {longest_presence:.1f}s ({presence_percentage:.1f}% of video)"
            else:
                return "Minimal person presence detected"
    
    def get_dwelling_summary(self, time_window=300):
        """
        Get summary of dwelling activity from recent video analyses
        
        Args:
            time_window: Time window in seconds (default: 5 minutes)
            
        Returns:
            dict: Dwelling activity summary
        """
        current_time = time.time()
        cutoff_time = current_time - time_window
        
        recent_analyses = [event for event in self.video_analysis_history 
                          if event['timestamp'] >= cutoff_time]
        
        if not recent_analyses:
            return {
                'total_videos_analyzed': 0,
                'dwelling_events': 0,
                'average_confidence': 0,
                'total_dwelling_time': 0
            }
        
        # Calculate statistics
        total_videos = len(recent_analyses)
        dwelling_events = len([a for a in recent_analyses if a['analysis']['dwelling_detected']])
        
        # Calculate average confidence for dwelling events
        dwelling_confidences = [a['analysis']['confidence'] for a in recent_analyses 
                               if a['analysis']['dwelling_detected']]
        avg_confidence = sum(dwelling_confidences) / len(dwelling_confidences) if dwelling_confidences else 0
        
        # Calculate total dwelling time
        total_dwelling_time = sum(a['analysis'].get('people_presence_time', 0) for a in recent_analyses)
        
        return {
            'total_videos_analyzed': total_videos,
            'dwelling_events': dwelling_events,
            'dwelling_rate': (dwelling_events / total_videos) * 100 if total_videos > 0 else 0,
            'average_confidence': round(avg_confidence, 2),
            'total_dwelling_time': round(total_dwelling_time, 1),
            'time_window_minutes': time_window / 60
        }
    
    def reset_history(self):
        """Reset analysis history (useful for testing or periodic cleanup)"""
        self.video_analysis_history.clear()
        print("Behavior analyzer history reset")
    
    def _create_error_result(self, message, error_detail):
        """Create standardized error result for failed video analysis"""
        return {
            'dwelling_detected': False,
            'confidence': 0.0,
            'total_detections': 0,
            'message': message,
            'error': error_detail,
            'analysis_success': False
        }
    
    def process_motion_capture_result(self, capture_result, yolo_handler):
        """
        Process the result from camera motion_triggered_capture()
        
        Args:
            capture_result: Result dict from CameraManager.motion_triggered_capture()
            yolo_handler: YOLOHandler instance
            
        Returns:
            dict: Complete analysis including dwelling detection
        """
        if not capture_result.get('success', False):
            return {
                'analysis_success': False,
                'dwelling_detected': False,
                'message': 'Motion capture failed',
                'capture_result': capture_result
            }
        
        video_file = capture_result.get('video')
        if not video_file:
            return {
                'analysis_success': False,
                'dwelling_detected': False,
                'message': 'No video file in capture result',
                'capture_result': capture_result
            }
        
        # Analyze the video for dwelling
        dwelling_analysis = self.analyze_video_for_dwelling(video_file, yolo_handler)
        
        return {
            'analysis_success': True,
            'dwelling_analysis': dwelling_analysis,
            'dwelling_detected': dwelling_analysis['dwelling_detected'],
            'confidence': dwelling_analysis['confidence'],
            'message': dwelling_analysis['message'],
            'capture_result': capture_result,
            'video_analyzed': video_file
        }
