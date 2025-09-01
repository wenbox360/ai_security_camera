"""
PIR Motion Sensor Handler
Detects motion using GPIO and triggers camera via events
"""

import time
import threading
import RPi.GPIO as GPIO
from config.settings import Settings

class PIRSensor:
    """PIR motion sensor interface with event-based communication"""
    
    def __init__(self, camera_manager=None):
        """Initialize PIR sensor on specified GPIO pin"""
        self.pin = Settings.get_pir_pin()
        self.motion_event = threading.Event()  # Event for communication with camera
        self.is_monitoring = False
        self.monitor_thread = None
        self.camera_manager = camera_manager  # Reference to camera for busy checking

    def setup(self):
        """Configure GPIO and sensor"""
        try:
            GPIO.setmode(GPIO.BOARD)
            GPIO.setup(self.pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitor_motion)
            self.monitor_thread.daemon = True  # Thread dies when main program ends
            self.monitor_thread.start()
            print("PIR sensor setup complete")
            return True
        except Exception as e:
            print(f"Error in PIR Sensor setup: {e}")
            return False

    def setup_check(self):
        """Check if GPIO is configured correctly"""
        try:
            GPIO.setup(self.pin, GPIO.IN)
            return True
        except Exception as e:
            print(f"Error in PIR Sensor setup_check: {e}")
            return False

    def is_motion_detected(self):
        """Check current if motion is detected"""
        try:
            return GPIO.input(self.pin) == GPIO.HIGH
        except Exception as e:
            print(f"Error in PIR Sensor is_motion_detected: {e}")
            return False
        
    def _monitor_motion(self):
        """Background thread to monitor motion and trigger events"""
        last_motion_time = 0
        debounce_delay = 10.0  # Increased to 10 seconds between detections
        consecutive_skips = 0
        max_consecutive_skips = 5
        
        while self.is_monitoring:
            try:
                current_time = time.time()
                
                if self.is_motion_detected():
                    # Debounce - prevent rapid triggers
                    if current_time - last_motion_time > debounce_delay:
                        # CHECK IF CAMERA IS BUSY - Don't trigger if busy
                        if self.camera_manager and self.camera_manager.camera_is_busy():
                            consecutive_skips += 1
                            if consecutive_skips <= max_consecutive_skips:
                                print(f"PIR: Motion detected but camera busy, skipping... ({consecutive_skips}/{max_consecutive_skips})")
                            elif consecutive_skips == max_consecutive_skips + 1:
                                print("PIR: Camera busy for too long, reducing frequency...")
                            time.sleep(2.0)  # Wait longer when camera is busy
                            continue
                        
                        # Reset skip counter on successful trigger
                        consecutive_skips = 0
                        last_motion_time = current_time
                        print(f"PIR: Motion detected at {time.strftime('%H:%M:%S')}")
                        
                        # SIGNAL CAMERA THREAD
                        self.motion_event.set()
                        
                        # Wait longer after triggering to prevent immediate retriggering
                        time.sleep(1.0)
                        self.motion_event.clear()
                        
                        # Additional cooldown period
                        time.sleep(2.0)
                    else:
                        # Still in debounce period
                        time.sleep(0.5)
                else:
                    # No motion detected, short sleep
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"PIR monitoring error: {e}")
                time.sleep(1.0)
    
    def wait_for_motion(self, timeout=None):
        """Wait for motion detection event - used by camera thread"""
        return self.motion_event.wait(timeout)
    
    def stop_monitoring(self):
        """Stop motion monitoring"""
        self.is_monitoring = False
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2.0)
    
    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop_monitoring()
        try:
            GPIO.cleanup(self.pin)
        except:
            pass

