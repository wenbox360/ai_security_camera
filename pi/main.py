"""
Main Security Camera System
Integrates PIR, Camera, YOLO, Face Recognition, and Dwelling Analysis
"""

import os
import sys
import time
import signal
import threading
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import system components
from sensors.pir import PIRSensor
from camera.camera_utils import CameraManager
from vision.yolo_handler import YOLOHandler
from vision.face_recognition import FaceRecognitionHandler
from inference.behavior_analyzer import BehaviorAnalyzer
from utils.security_logger import SecurityLogger
from utils.config_queue import ConfigurationQueue
from config.settings import Settings

class SecurityCameraSystem:
    """Main security camera system orchestrator"""
    
    def __init__(self):
        """Initialize the security system"""
        print("🔐 Initializing AI Security Camera System...")
        
        # System components
        self.camera_manager = None
        self.pir_sensor = None
        self.yolo_handler = None
        self.face_recognition = None
        self.behavior_analyzer = None
        self.security_logger = None
        self.config_queue = None
        
        # System state
        self.is_running = False
        self.system_ready = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def initialize_system(self):
        """Initialize all system components"""
        try:
            print("📁 Creating capture directories...")
            self._ensure_directories()
            
            print("📝 Initializing security logger...")
            self.security_logger = SecurityLogger()
            
            print("📷 Initializing camera manager...")
            self.camera_manager = CameraManager()
            if not self.camera_manager.setup():
                raise Exception("Camera initialization failed")
            
            # Set motion callback to process events
            self.camera_manager.set_motion_callback(self.process_motion_event)
            
            print("🎯 Loading YOLO model...")
            self.yolo_handler = YOLOHandler()
            
            print("👤 Initializing face recognition...")
            self.face_recognition = FaceRecognitionHandler()
            
            print("🧠 Initializing behavior analyzer...")
            self.behavior_analyzer = BehaviorAnalyzer()
            
            print("📡 Initializing PIR sensor...")
            self.pir_sensor = PIRSensor(camera_manager=self.camera_manager)
            if not self.pir_sensor.setup():
                raise Exception("PIR sensor initialization failed")
            
            # Start camera motion monitoring
            print("🎬 Starting camera motion monitoring...")
            self.camera_manager.start_motion_monitoring(self.pir_sensor)
            
            # Initialize configuration queue
            print("📋 Initializing configuration queue...")
            self.config_queue = ConfigurationQueue(security_system=self)
            
            self.system_ready = True
            print("✅ Security system initialization complete!")
            return True
            
        except Exception as e:
            print(f"❌ System initialization failed: {e}")
            return False
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        file_paths = Settings.get_file_paths()
        directories = [
            file_paths['captures'],
            file_paths['snapshots'], 
            file_paths['videos'],
            os.path.join(file_paths['captures'], 'logs')
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
    
    def start_monitoring(self):
        """Start the main monitoring loop"""
        if not self.system_ready:
            print("❌ System not ready. Please initialize first.")
            return False
        
        print("🚀 Starting security monitoring...")
        print("👀 Monitoring for motion events...")
        print("📊 System Status:")
        print(f"   - PIR Sensor: {'✅ Active' if self.pir_sensor.is_monitoring else '❌ Inactive'}")
        print(f"   - Camera: {'✅ Ready' if self.camera_manager.is_initialized else '❌ Not Ready'}")
        print(f"   - YOLO Model: ✅ Loaded ({Settings.get_yolo_model()})")
        print(f"   - Face Recognition: ✅ Ready")
        print(f"   - Config Queue: ✅ Active")
        print("Press Ctrl+C to stop monitoring...\n")
        
        self.is_running = True
        
        try:
            # Main monitoring loop
            while self.is_running:
                # Check for motion capture results
                # Note: The actual motion detection happens in background threads
                # Here we just keep the main thread alive and could add periodic tasks
                
                time.sleep(1)  # Check every second
                
                # Optional: Add periodic status checks, cleanup, etc.
                
        except KeyboardInterrupt:
            print("\n🛑 Monitoring stopped by user")
        except Exception as e:
            print(f"\n❌ Monitoring error: {e}")
        finally:
            self.shutdown_system()
    
    def process_motion_event(self, capture_result):
        """
        Process a motion detection event with full analysis
        This method would be called by the camera system when motion is detected
        """
        print(f"\n🎯 Processing motion event at {datetime.now().strftime('%H:%M:%S')}")
        
        if not capture_result.get('success', False):
            print("❌ Motion capture failed")
            return
        
        # Step 1: Analyze video for dwelling behavior
        print("🧠 Analyzing video for dwelling behavior...")
        dwelling_result = self.behavior_analyzer.process_motion_capture_result(
            capture_result, self.yolo_handler
        )
        
        if not dwelling_result['analysis_success']:
            print(f"❌ Dwelling analysis failed: {dwelling_result['message']}")
            return
        
        dwelling_analysis = dwelling_result['dwelling_analysis']
        people_detected = dwelling_analysis.get('total_detections', 0) > 0
        
        print(f"📊 Dwelling Analysis: {dwelling_analysis['message']}")
        
        # Step 2: Face recognition if people detected
        known_people = []
        unknown_people = []
        face_analysis = None
        
        if people_detected:
            print("👤 People detected - running face recognition...")
            
            # Get snapshot for face recognition
            snapshot_file = capture_result.get('snapshot')
            if snapshot_file:
                face_analysis = self.face_recognition.analyze_frame_for_threats(snapshot_file)
                
                # Parse face recognition results
                if face_analysis.get('faces_detected', 0) > 0:
                    known_people = face_analysis.get('recognized_faces', [])
                    unknown_people = face_analysis.get('unknown_faces', 0)
                    
                    print(f"👥 Face Recognition Results:")
                    print(f"   - Faces detected: {face_analysis.get('faces_detected', 0)}")
                    print(f"   - Known people: {len(known_people)}")
                    print(f"   - Unknown people: {unknown_people}")
                else:
                    print("👤 No faces detected in frame")
            else:
                print("⚠️  No snapshot available for face recognition")
        
        # Step 3: Determine alert level and log event
        self._evaluate_security_event(dwelling_analysis, known_people, unknown_people, face_analysis)
    
    def _evaluate_security_event(self, dwelling_analysis, known_people, unknown_people, face_analysis):
        """Evaluate security event and determine appropriate response"""
        
        # Log the event
        log_entry = self.security_logger.log_dwelling_event(
            dwelling_analysis, known_people, unknown_people
        )
        
        # Log face recognition if available
        if face_analysis:
            self.security_logger.log_face_recognition_event(face_analysis)
        
        # Determine response based on analysis
        dwelling_detected = dwelling_analysis['dwelling_detected']
        has_unknown_people = unknown_people > 0
        
        if dwelling_detected and has_unknown_people:
            print("🚨 SECURITY ALERT: Unknown person dwelling detected!")
            print(f"   Duration: {dwelling_analysis.get('longest_continuous_presence', 0):.1f}s")
            print(f"   Confidence: {dwelling_analysis['confidence']:.2f}")
            print(f"   Unknown people: {unknown_people}")
            
        elif dwelling_detected and known_people:
            print("⚠️  Known person dwelling detected")
            print(f"   Duration: {dwelling_analysis.get('longest_continuous_presence', 0):.1f}s")
            print(f"   Known people: {', '.join([p.get('name', 'Unknown') for p in known_people])}")
            
        elif has_unknown_people:
            print("👁️  Unknown person detected (brief presence)")
            
        elif known_people:
            print("✅ Known person detected")
            print(f"   People: {', '.join([p.get('name', 'Unknown') for p in known_people])}")
            
        else:
            print("ℹ️  Motion detected - person analysis inconclusive")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.is_running = False
    
    def shutdown_system(self):
        """Gracefully shutdown the system"""
        print("🔄 Shutting down security system...")
        
        try:
            if self.pir_sensor:
                print("📡 Stopping PIR sensor...")
                self.pir_sensor.cleanup()
            
            if self.camera_manager:
                print("📷 Stopping camera...")
                self.camera_manager.cleanup()
            
            if self.config_queue:
                print("📋 Stopping configuration queue...")
                self.config_queue.cleanup()
            
            print("✅ Security system shutdown complete")
            
        except Exception as e:
            print(f"⚠️  Warning during shutdown: {e}")
    
    def get_system_status(self):
        """Get current system status"""
        return {
            'system_ready': self.system_ready,
            'is_running': self.is_running,
            'camera_ready': self.camera_manager.is_initialized if self.camera_manager else False,
            'pir_active': self.pir_sensor.is_monitoring if self.pir_sensor else False,
            'camera_busy': self.camera_manager.camera_is_busy() if self.camera_manager else False,
            'config_queue': self.config_queue.get_queue_status() if self.config_queue else None
        }
    
    # Configuration API methods (for external access)
    def update_yolo_confidence(self, confidence: float, priority: int = 1) -> str:
        """Update YOLO confidence threshold via configuration queue"""
        if not self.config_queue:
            return None
        return self.config_queue.update_yolo_confidence(confidence, priority)
    
    def add_trusted_person(self, name: str, image_data: bytes, priority: int = 1) -> str:
        """Add trusted person via configuration queue"""
        if not self.config_queue:
            return None
        return self.config_queue.add_trusted_person(name, image_data, priority)
    
    def remove_trusted_person(self, name: str, priority: int = 1) -> str:
        """Remove trusted person via configuration queue"""
        if not self.config_queue:
            return None
        return self.config_queue.remove_trusted_person(name, priority)
    
    def update_dwelling_threshold(self, threshold: float, priority: int = 1) -> str:
        """Update dwelling detection threshold via configuration queue"""
        if not self.config_queue:
            return None
        return self.config_queue.update_dwelling_threshold(threshold, priority)
    
    def get_config_request_status(self, request_id: str):
        """Get status of a configuration request"""
        if not self.config_queue:
            return None
        return self.config_queue.get_request_status(request_id)


def main():
    """Main entry point"""
    print("🎯 AI Security Camera System v1.0")
    print("=" * 50)
    
    # Create and initialize system
    security_system = SecurityCameraSystem()
    
    if security_system.initialize_system():
        # Start monitoring
        security_system.start_monitoring()
    else:
        print("❌ Failed to initialize security system")
        sys.exit(1)


if __name__ == "__main__":
    main()
