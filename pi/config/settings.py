
"""
Configuration settings for the security camera system
"""

# PIR Sensor Settings
PIR_PIN = 18
PIR_SENSITIVITY_DELAY = 2.0

# Camera Settings - High Resolution (for snapshots)
CAMERA_HIGH_RES_WIDTH = 1920
CAMERA_HIGH_RES_HEIGHT = 1080
CAMERA_HIGH_RES_FORMAT = "RGB888"

# Camera Settings - Low Resolution (for video)
CAMERA_LOW_RES_WIDTH = 640
CAMERA_LOW_RES_HEIGHT = 480
CAMERA_LOW_RES_FORMAT = "RGB888"

# Video Settings
VIDEO_DURATION = 2  # seconds
VIDEO_BITRATE = 1000000  # 1Mbps
VIDEO_FORMAT = "h264"

# File Settings
CAPTURES_DIR = "captures/"
SNAPSHOTS_DIR = "captures/snapshots/"
VIDEOS_DIR = "captures/videos/"

# Yolo Model Settings
YOLO_MODEL = "yolo11n.pt"

class Settings:
    """Settings configuration class"""
    
    @staticmethod
    def get_pir_pin():
        return PIR_PIN
    
    @staticmethod
    def get_high_res_config():
        return {
            "format": CAMERA_HIGH_RES_FORMAT,
            "size": (CAMERA_HIGH_RES_WIDTH, CAMERA_HIGH_RES_HEIGHT)
        }
    
    @staticmethod
    def get_low_res_config():
        return {
            "format": CAMERA_LOW_RES_FORMAT,
            "size": (CAMERA_LOW_RES_WIDTH, CAMERA_LOW_RES_HEIGHT)
        }
    
    @staticmethod
    def get_video_settings():
        return {
            "duration": VIDEO_DURATION,
            "bitrate": VIDEO_BITRATE,
            "format": VIDEO_FORMAT
        }
    
    @staticmethod
    def get_file_paths():
        return {
            "captures": CAPTURES_DIR,
            "snapshots": SNAPSHOTS_DIR,
            "videos": VIDEOS_DIR
        }
    
    @staticmethod
    def get_yolo_model():
        return YOLO_MODEL