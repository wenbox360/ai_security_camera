"""
Main Security Camera System
Integrates PIR, Camera, YOLO, Face Recognition, and Dwelling Analysis
"""

import os
import sys
import time
import signal
import cv2
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
                # Load the image file as numpy array for face recognition
                try:
                    snapshot_frame = cv2.imread(snapshot_file)
                    if snapshot_frame is not None:
                        # Convert BGR to RGB for face_recognition library
                        snapshot_frame = cv2.cvtColor(snapshot_frame, cv2.COLOR_BGR2RGB)
                        face_analysis = self.face_recognition.analyze_frame_for_threats(snapshot_frame)
                    else:
                        print(f"❌ Could not load snapshot file: {snapshot_file}")
                        face_analysis = {'threat_detected': False, 'total_faces': 0, 'message': 'Could not load snapshot'}
                except Exception as e:
                    print(f"❌ Error loading snapshot for face recognition: {e}")
                    face_analysis = {'threat_detected': False, 'total_faces': 0, 'message': f'Error loading snapshot: {e}'}
                
                # Parse face recognition results
                if face_analysis.get('total_faces', 0) > 0:
                    known_count = face_analysis.get('known_faces', 0)
                    unknown_count = face_analysis.get('unknown_faces', 0)
                    faces_list = face_analysis.get('faces', [])
                    
                    print(f"👥 Face Recognition Results:")
                    print(f"   - Total faces: {face_analysis.get('total_faces', 0)}")
                    print(f"   - Known people: {known_count}")
                    print(f"   - Unknown people: {unknown_count}")
                    print(f"   - Message: {face_analysis.get('message', 'N/A')}")
                else:
                    print("👤 No faces detected in frame")
            else:
                print("⚠️  No snapshot available for face recognition")
        
        # Step 3: Determine alert level and log event
        self._evaluate_security_event(dwelling_analysis, known_people, unknown_people, face_analysis)
    
    def _evaluate_security_event(self, dwelling_analysis, known_people, unknown_people, face_analysis):
        """Evaluate security event and determine appropriate response"""
        
        # Ensure known_people and unknown_people are properly handled
        if isinstance(known_people, list):
            known_people_count = len(known_people)
            known_people_list = known_people
        else:
            known_people_count = known_people if known_people else 0
            known_people_list = []
            
        if isinstance(unknown_people, list):
            unknown_people_count = len(unknown_people)
        else:
            unknown_people_count = unknown_people if unknown_people else 0
        
        try:
            # Log the event
            log_entry = self.security_logger.log_dwelling_event(
                dwelling_analysis, known_people_count, unknown_people_count
            )
            
            # Log face recognition if available
            if face_analysis:
                self.security_logger.log_face_recognition_event(face_analysis)
        except Exception as e:
            print(f"Motion callback error: {e}")
            return
        
        # Determine response based on analysis
        dwelling_detected = dwelling_analysis.get('dwelling_detected', False)
        has_unknown_people = unknown_people_count > 0
        
        if dwelling_detected and has_unknown_people:
            print("🚨 SECURITY ALERT: Unknown person dwelling detected!")
            print(f"   Duration: {dwelling_analysis.get('longest_continuous_presence', 0):.1f}s")
            print(f"   Confidence: {dwelling_analysis.get('confidence', 0):.2f}")
            print(f"   Unknown people: {unknown_people_count}")
            
        elif dwelling_detected and known_people_count > 0:
            print("⚠️  Known person dwelling detected")
            print(f"   Duration: {dwelling_analysis.get('longest_continuous_presence', 0):.1f}s")
            if known_people_list:
                names = [p.get('name', 'Unknown') for p in known_people_list]
                print(f"   Known people: {', '.join(names)}")
            
        elif has_unknown_people:
            print("👁️  Unknown person detected (brief presence)")
            
        elif known_people_count > 0:
            print("✅ Known person detected")
            if known_people_list:
                names = [p.get('name', 'Unknown') for p in known_people_list]
                print(f"   People: {', '.join(names)}")
            
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
