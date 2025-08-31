"""
Camera utilities for PiCamera2
"""

import time
import threading
import numpy as np
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder, MJPEGEncoder
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
            
            # Switch to photo configuration with better error handling
            try:
                self.picam2.switch_mode(self.photo_config)
                time.sleep(1.0)  # Increased settling time for mode switch
                print("Camera Thread: Photo mode activated")
            except Exception as mode_error:
                print(f"Camera Thread: Photo mode switch error: {mode_error}")
                # Try to recover
                try:
                    self.picam2.stop()
                    time.sleep(0.5)
                    self.picam2.start()
                    time.sleep(0.5)
                    self.picam2.switch_mode(self.photo_config)
                    time.sleep(1.0)
                    print("Camera Thread: Photo mode recovered")
                except Exception as recovery_error:
                    print(f"Camera Thread: Photo mode recovery failed: {recovery_error}")
                    raise
            
            # Capture high-res photo
            self.picam2.capture_file(filename)
            print(f"High-res snapshot saved: {filename}")
            return filename
            
        except Exception as e:
            print(f"Snapshot capture failed: {e}")
            return None
    
    def record_low_res_video(self, filename=None):
        """Record low resolution video for specified duration with proper H.264 finalization"""
        if not self.is_initialized:
            print("Camera not initialized")
            return None
            
        try:
            # Generate filename if not provided
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{self.file_paths['videos']}video_{timestamp}.{self.video_settings['format']}"
            
            # Switch to video configuration with better error handling
            try:
                self.picam2.switch_mode(self.video_config)
                time.sleep(1.0)  # Increased settling time for mode switch
                print("Camera Thread: Video mode activated")
            except Exception as mode_error:
                print(f"Camera Thread: Mode switch error: {mode_error}")
                # Try to recover by stopping and restarting
                try:
                    self.picam2.stop()
                    time.sleep(0.5)
                    self.picam2.start()
                    time.sleep(0.5)
                    self.picam2.switch_mode(self.video_config)
                    time.sleep(1.0)
                    print("Camera Thread: Video mode recovered")
                except Exception as recovery_error:
                    print(f"Camera Thread: Mode recovery failed: {recovery_error}")
                    raise
            
            # Setup encoder with improved settings for metadata integrity
            encoder = H264Encoder(
                bitrate=self.video_settings["bitrate"],
                repeat=True,  # Ensures proper frame sequencing
                iperiod=30   # Insert I-frames every 30 frames for better seeking
            )
            
            # Start recording
            self.picam2.start_recording(encoder, filename)
            print(f"Started recording video: {filename}")
            
            # Record for specified duration
            time.sleep(self.video_settings["duration"])
            
            # Ensure proper stream finalization
            try:
                # Give encoder time to finalize current frame
                time.sleep(0.1)
                
                # Stop recording gracefully
                self.picam2.stop_recording()
                
                # Additional time for encoder to write final metadata
                time.sleep(0.2)
                
            except Exception as stop_error:
                print(f"Warning during recording stop: {stop_error}")
                # Still try to clean up
                try:
                    self.picam2.stop_recording()
                except:
                    pass
            
            print(f"Video recording complete: {filename}")
            
            # Verify the file was created and has reasonable size
            import os
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                if file_size < 1000:  # Less than 1KB is suspicious
                    print(f"⚠️  Warning: Video file suspiciously small ({file_size} bytes)")
                else:
                    print(f"✅ Video file created successfully ({file_size} bytes)")
            else:
                print(f"❌ Video file was not created: {filename}")
                return None
                
            return filename
            
        except Exception as e:
            print(f"Video recording failed: {e}")
            # Ensure recording is stopped even on error
            try:
                self.picam2.stop_recording()
            except:
                pass
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
            # Strategy: Record video FIRST, then capture snapshot
            # This avoids the problematic photo->video mode switch that can corrupt H.264
            
            # Record low-res video FIRST
            print("Camera Thread: Recording video first to avoid mode switching issues...")
            video_file = self.record_low_res_video()
            
            # Give camera time to fully complete video recording and reset
            time.sleep(0.5)
            
            # Capture high-res snapshot AFTER video
            print("Camera Thread: Now capturing snapshot...")
            snapshot_file = self.capture_high_res_snapshot()
            
            capture_info = {
                'timestamp': datetime.now().isoformat(),
                'snapshot': snapshot_file,
                'video': video_file,
                'success': bool(snapshot_file and video_file)
            }
            
            if capture_info['success']:
                print("Motion capture complete!")
                print(f"   Video: {video_file}")
                print(f"   Snapshot: {snapshot_file}")
                
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
            consecutive_busy_count = 0
            max_consecutive_busy = 3
            
            while True:
                try:
                    # WAIT FOR MOTION EVENT FROM PIR
                    if pir_sensor and pir_sensor.wait_for_motion(timeout=10):
                        print("Camera Thread: Motion event received!")
                        
                        # Check if camera is already busy
                        if self.camera_busy.is_set():
                            consecutive_busy_count += 1
                            if consecutive_busy_count <= max_consecutive_busy:
                                print(f"Camera Thread: Camera busy, skipping motion event ({consecutive_busy_count}/{max_consecutive_busy})")
                            elif consecutive_busy_count == max_consecutive_busy + 1:
                                print("Camera Thread: Camera busy for too long, will force reset soon...")
                            elif consecutive_busy_count >= max_consecutive_busy + 5:
                                print("Camera Thread: Forcing camera reset due to extended busy state")
                                self.camera_busy.clear()
                                consecutive_busy_count = 0
                            continue
                        
                        # Reset consecutive busy counter on successful processing
                        consecutive_busy_count = 0
                        
                        # Trigger dual capture in current thread to maintain control
                        self.motion_triggered_capture()
                        
                    else:
                        # Timeout - just continue monitoring
                        time.sleep(0.1)  # Small delay to prevent excessive CPU usage
                        continue
                        
                except Exception as e:
                    print(f"Motion monitoring error: {e}")
                    # Clear busy flag on error to prevent permanent lock
                    self.camera_busy.clear()
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
            # Clear busy flag first
            self.camera_busy.clear()
            
            # Stop any ongoing operations
            if self.picam2:
                try:
                    self.picam2.stop()
                except:
                    pass  # Ignore if already stopped
                    
                try:
                    self.picam2.close()
                except:
                    pass  # Ignore if already closed
                    
            self.is_initialized = False
            print("Camera cleaned up")
            
        except Exception as e:
            print(f"Camera cleanup error: {e}")
            # Force cleanup even if errors occur
            self.camera_busy.clear()
            self.is_initialized = False