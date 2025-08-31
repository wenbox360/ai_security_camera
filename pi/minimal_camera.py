"""
MINIMAL Camera Manager - Bare bones for debugging frame count issue
"""

import time
from datetime import datetime
from picamera2 import Picamera2
from picamera2.encoders import H264Encoder

class MinimalCameraManager:
    """Stripped down camera manager"""
    
    def __init__(self):
        self.picam2 = None
        self.is_initialized = False
    
    def setup(self):
        """Minimal camera setup"""
        try:
            self.picam2 = Picamera2()
            
            # Simple video config only
            self.video_config = self.picam2.create_video_configuration(
                main={"format": "RGB888", "size": (640, 480)}
            )
            
            self.picam2.configure(self.video_config)
            self.picam2.start()
            time.sleep(2)
            
            self.is_initialized = True
            print("✅ Minimal camera setup complete")
            return True
            
        except Exception as e:
            print(f"❌ Camera setup failed: {e}")
            return False
    
    def record_video(self, duration=2, format="mp4"):
        """Record a simple video"""
        if not self.is_initialized:
            return None
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"minimal_video_{timestamp}.{format}"
            
            print(f"🔴 Recording {format.upper()}: {filename}")
            
            # Simple encoder
            encoder = H264Encoder(bitrate=1000000)
            
            self.picam2.start_recording(encoder, filename)
            time.sleep(duration)
            self.picam2.stop_recording()
            
            print(f"✅ Recording complete: {filename}")
            return filename
            
        except Exception as e:
            print(f"❌ Recording failed: {e}")
            try:
                self.picam2.stop_recording()
            except:
                pass
            return None
    
    def cleanup(self):
        """Clean up camera"""
        try:
            if self.picam2:
                self.picam2.close()
            print("🧹 Camera cleaned up")
        except Exception as e:
            print(f"⚠️  Cleanup error: {e}")
