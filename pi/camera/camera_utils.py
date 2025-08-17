"""
Camera utilities for PiCamera2
"""

import time
import threading
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder
from config.settings import Settings

class CameraManager:
    """Camera manager with dual capture capabilities"""
    
    def __init__(self, motion_callback=None):
        """Initialize camera manager"""
        self.picam2 = None
        self.is_initialized = False
        self.capture_thread = None
        self.camera_busy = threading.Event()  # Event to signal camera is busy
        self.motion_callback = motion_callback  # Callback for motion events
        
        # Get configurations from settings
        self.high_res_config = Settings.get_high_res_config()
        self.low_res_config = Settings.get_low_res_config()
        self.video_settings = Settings.get_video_settings()
        self.file_paths = Settings.get_file_paths()

    def setup(self):
        """Initialize camera"""
        try:
            self.picam2 = Picamera2()
            
            # Configure camera for both photo and video
            self.photo_config = self.picam2.create_still_configuration(
                main=self.high_res_config
            )
            
            self.video_config = self.picam2.create_video_configuration(
                main=self.low_res_config
            )
            
            # Start with photo config
            self.picam2.configure(self.photo_config)
            self.picam2.start()
            time.sleep(2)  # Camera stabilization
            
            self.is_initialized = True
            print("Camera initialized successfully")
            return True
            
        except Exception as e:
            print(f"Camera setup failed: {e}")
            return False
    
    def capture_high_res_snapshot(self, filename=None):
        """Capture high resolution snapshot"""
        if not self.is_initialized:
            print("Camera not initialized")
            return None
            
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.file_paths['snapshots']}snapshot_{timestamp}.jpg"
            
            # Switch to photo configuration
            self.picam2.switch_mode(self.photo_config)
            time.sleep(0.5)  # Let camera adjust
            
            # Capture high-res photo
            self.picam2.capture_file(filename)
            print(f"High-res snapshot saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"Snapshot capture failed: {e}")
            return None
    
    def record_low_res_video(self, filename=None):
        """Record low resolution video for specified duration"""
        if not self.is_initialized:
            print("Camera not initialized")
            return None
            
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.file_paths['videos']}video_{timestamp}.{self.video_settings['format']}"
            
            # Switch to video configuration
            self.picam2.switch_mode(self.video_config)
            time.sleep(0.5)  # Let camera adjust
            
            # Setup encoder
            encoder = H264Encoder(bitrate=self.video_settings["bitrate"])
            
            # Start recording
            self.picam2.start_recording(encoder, filename)
            print(f"Started recording video: {filename}")
            
            # Record for specified duration
            time.sleep(self.video_settings["duration"])

            # Stop recording
            self.picam2.stop_recording()
            print(f"Video recording complete: {filename}")
            return filename
            
        except Exception as e:
            print(f"Video recording failed: {e}")
            return None
    
    def motion_triggered_capture(self):
        """
        Handle motion detection - captures both snapshot and video
        This runs in a separate thread when motion is detected
        """
        # SET CAMERA AS BUSY
        self.camera_busy.set()
        print("Camera Thread: Motion triggered! Starting dual capture...")
        
        try:
            # Capture high-res snapshot first (quick)
            snapshot_file = self.capture_high_res_snapshot()
            
            # Record low-res video
            video_file = self.record_low_res_video()
            
            capture_info = {
                'timestamp': datetime.now().isoformat(),
                'snapshot': snapshot_file,
                'video': video_file,
                'success': bool(snapshot_file and video_file)
            }
            
            if capture_info['success']:
                print("Motion capture complete!")
                print(f"   Snapshot: {snapshot_file}")
                print(f"   Video: {video_file}")
                
                # Trigger callback for motion event processing
                if self.motion_callback:
                    try:
                        self.motion_callback(capture_info)
                    except Exception as e:
                        print(f"Motion callback error: {e}")
            else:
                print("Motion capture partially failed")
                
            return capture_info
            
        except Exception as e:
            print(f"Motion capture error: {e}")
            return {'success': False, 'error': str(e)}
        
        finally:
            # CLEAR CAMERA BUSY FLAG
            self.camera_busy.clear()
            print("Camera Thread: Camera available again")
    
    def start_motion_monitoring(self, pir_sensor):
        """
        Start monitoring for motion events from PIR sensor
        Runs in background thread
        """
        def motion_worker():
            while True:
                try:
                    # WAIT FOR MOTION EVENT FROM PIR
                    if pir_sensor and pir_sensor.wait_for_motion(timeout=10):
                        print("Camera Thread: Motion event received!")
                        
                        # Trigger dual capture in separate thread to avoid blocking
                        capture_thread = threading.Thread(target=self.motion_triggered_capture)
                        capture_thread.daemon = True
                        capture_thread.start()
                        
                    else:
                        # Timeout - just continue monitoring
                        time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                        continue
                        
                except Exception as e:
                    print(f"Motion monitoring error: {e}")
                    time.sleep(1)
        
        # Start the motion monitoring thread
        self.capture_thread = threading.Thread(target=motion_worker)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        print("Camera motion monitoring started")
        print(f"   Snapshots: {self.file_paths['snapshots']}")
        print(f"   Videos: {self.file_paths['videos']}")
        print(f"   Video duration: {self.video_settings['duration']}s")
    
    def camera_is_busy(self):
        """Check if camera is currently busy with capture"""
        return self.camera_busy.is_set()
    
    def set_motion_callback(self, callback):
        """Set callback function for motion events"""
        self.motion_callback = callback
    
    def get_camera_info(self):
        """Get camera status information"""
        return {
            'initialized': self.is_initialized,
            'busy': self.camera_busy.is_set(),
            'high_res_config': self.high_res_config,
            'low_res_config': self.low_res_config,
            'video_settings': self.video_settings,
            'file_paths': self.file_paths
        }
    
    def cleanup(self):
        """Clean up camera resources"""
        try:
            # Clear busy flag
            self.camera_busy.clear()
            
            if self.picam2:
                self.picam2.stop()
                self.picam2.close()
                
            self.is_initialized = False
            print("Camera cleaned up")
            
        except Exception as e:
            print(f"Camera cleanup error: {e}")