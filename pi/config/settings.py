
"""
Configuration settings for the security camera system
"""

# PIR Sensor Settings
PIR_PIN = 11
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
VIDEO_DURATION = 1  # seconds - reduced from 2 to minimize processing time
VIDEO_BITRATE = 800000  # 800kbps - reduced bitrate for faster processing
VIDEO_FORMAT = "h264"  # Keep as h264 but with improved encoding

# File Settings
CAPTURES_DIR = "captures/"
SNAPSHOTS_DIR = "captures/snapshots/"
VIDEOS_DIR = "captures/videos/"

# Face Recognition Settings
FACE_EMBEDDINGS_FILE = "captures/known_faces/embeddings.json"
FACE_IMAGES_DIR = "captures/known_faces/images/"
FACE_METADATA_FILE = "captures/known_faces/metadata.json"

# Yolo Model Settings
YOLO_MODEL = "yolo11n.pt"

# Behavior Analysis Settings - Video-based Dwelling Detection
DWELLING_THRESHOLD = 30  # seconds - minimum time to consider dwelling
VIDEO_FRAME_SKIP = 3  # analyze every nth frame for efficiency
MIN_PERSON_CONFIDENCE = 0.5  # minimum YOLO confidence for person detection

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
    def get_face_embeddings_path():
        """Get path to face embeddings file"""
        return FACE_EMBEDDINGS_FILE
    
    @staticmethod
    def get_face_images_dir():
        """Get directory for face images"""
        return FACE_IMAGES_DIR
    
    @staticmethod
    def get_face_metadata_path():
        """Get path to face metadata file"""
        return FACE_METADATA_FILE
    
    @staticmethod
    def get_yolo_model():
        return YOLO_MODEL
    
    @staticmethod
    def get_loitering_threshold():
        """Get dwelling threshold in seconds"""
        return DWELLING_THRESHOLD
    
    @staticmethod
    def get_video_frame_skip():
        """Get frame skip interval for video analysis"""
        return VIDEO_FRAME_SKIP
    
    @staticmethod
    def get_min_person_confidence():
        """Get minimum confidence for person detection"""
        return MIN_PERSON_CONFIDENCE