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
        debounce_delay = 5.0  # Wait 5 seconds between detections
        
        while self.is_monitoring:
            if self.is_motion_detected():
                current_time = time.time()
                
                # Debounce - prevent rapid triggers
                if current_time - last_motion_time > debounce_delay:
                    # CHECK IF CAMERA IS BUSY - Don't trigger if busy
                    if self.camera_manager and self.camera_manager.camera_is_busy():
                        print(f"PIR: Motion detected but camera busy, skipping...")
                        time.sleep(0.1)
                        continue
                    
                    last_motion_time = current_time
                    print(f"PIR: Motion detected at {time.strftime('%H:%M:%S')}")
                    
                    # SIGNAL CAMERA THREAD ONLY IF NOT BUSY
                    self.motion_event.set()
                    
                    # Keep event set briefly then clear
                    time.sleep(0.1)
                    self.motion_event.clear()
            
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage
    
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

