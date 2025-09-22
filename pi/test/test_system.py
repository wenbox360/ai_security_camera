"""
Test script for the AI Security Camera System
Tests individual components and their integration
"""

import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all components can be imported"""
    print("🔍 Testing imports...")
    
    try:
        from config.settings import Settings
        print("✅ Settings imported")
        
        from utils.security_logger import SecurityLogger
        print("✅ Security Logger imported")
        
        from vision.yolo_handler import YOLOHandler
        print("✅ YOLO Handler imported")
        
        from vision.face_recognition import FaceRecognitionHandler
        print("✅ Face Recognition imported")
        
        from inference.behavior_analyzer import BehaviorAnalyzer
        print("✅ Behavior Analyzer imported")
        
        from utils.config_queue import ConfigurationQueue
        print("✅ Configuration Queue imported")
        
        # Camera and PIR require hardware, so test separately
        print("📷 Testing camera import...")
        from camera.camera_utils import CameraManager
        print("✅ Camera Manager imported")
        
        print("📡 Testing PIR import...")
        from sensors.pir import PIRSensor
        print("✅ PIR Sensor imported")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_settings():
    """Test settings configuration"""
    print("\n🔧 Testing settings...")
    
    try:
        from config.settings import Settings
        
        # Test basic settings
        print(f"   YOLO Model: {Settings.get_yolo_model()}")
        print(f"   Dwelling Threshold: {Settings.get_loitering_threshold()}s")
        print(f"   Frame Skip: {Settings.get_video_frame_skip()}")
        print(f"   Min Confidence: {Settings.get_min_person_confidence()}")
        
        file_paths = Settings.get_file_paths()
        print(f"   Capture Dir: {file_paths['captures']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

def test_logger():
    """Test security logger"""
    print("\n📝 Testing security logger...")
    
    try:
        from utils.security_logger import SecurityLogger
        
        logger = SecurityLogger()
        
        # Test logging
        test_event = logger.log_security_event(
            'test_event', 
            {'message': 'System test'}, 
            'INFO'
        )
        
        print("✅ Security logger working")
        return True
        
    except Exception as e:
        print(f"❌ Logger test failed: {e}")
        return False

def test_yolo_handler():
    """Test YOLO handler initialization"""
    print("\n🎯 Testing YOLO handler...")
    
    try:
        from vision.yolo_handler import YOLOHandler
        
        yolo = YOLOHandler()
        print("✅ YOLO handler initialized")
        
        # Test if model file exists
        from config.settings import Settings
        model_path = Settings.get_yolo_model()
        if os.path.exists(model_path):
            print(f"✅ YOLO model file found: {model_path}")
        else:
            print(f"⚠️  YOLO model file not found: {model_path}")
            print("   You'll need to download the model file")
        
        return True
        
    except Exception as e:
        print(f"❌ YOLO test failed: {e}")
        return False

def test_face_recognition():
    """Test face recognition handler"""
    print("\n👤 Testing face recognition...")
    
    try:
        from vision.face_recognition import FaceRecognitionHandler
        
        face_rec = FaceRecognitionHandler()
        print("✅ Face recognition handler initialized")
        
        # Check if known faces directory exists
        if hasattr(face_rec, 'known_faces_file'):
            faces_dir = os.path.dirname(face_rec.known_faces_file)
            if os.path.exists(faces_dir):
                print(f"✅ Known faces directory exists: {faces_dir}")
            else:
                print(f"ℹ️  Known faces directory will be created: {faces_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ Face recognition test failed: {e}")
        return False

def test_behavior_analyzer():
    """Test behavior analyzer"""
    print("\n🧠 Testing behavior analyzer...")
    
    try:
        from inference.behavior_analyzer import BehaviorAnalyzer
        
        analyzer = BehaviorAnalyzer()
        print("✅ Behavior analyzer initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ Behavior analyzer test failed: {e}")
        return False

def test_config_queue():
    """Test configuration queue"""
    print("\n📋 Testing configuration queue...")
    
    try:
        from utils.config_queue import ConfigurationQueue, ConfigAction
        
        # Test queue initialization
        config_queue = ConfigurationQueue()
        print("✅ Configuration queue initialized")
        
        # Test adding requests
        request_id = config_queue.add_request(
            ConfigAction.UPDATE_YOLO_CONFIG,
            {'min_confidence': 0.8},
            priority=1
        )
        print(f"✅ Request queued: {request_id}")
        
        # Test queue status
        status = config_queue.get_queue_status()
        print(f"✅ Queue status: {status}")
        
        # Test API methods
        req_id = config_queue.update_yolo_confidence(0.9)
        print(f"✅ API method test: {req_id}")
        
        # Cleanup
        config_queue.cleanup()
        print("✅ Configuration queue cleaned up")
        
        return True
        
    except Exception as e:
        print(f"❌ Configuration queue test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🔬 AI Security Camera System - Component Tests")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_settings,
        test_logger,
        test_yolo_handler,
        test_face_recognition,
        test_behavior_analyzer,
        test_config_queue
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test error: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! System ready for integration.")
    else:
        print("⚠️  Some tests failed. Check the issues above.")
        
    # Show next steps
    print("\n📋 Next Steps:")
    print("1. Ensure YOLO model file (yolo11n.pt) is downloaded")
    print("2. Test on Raspberry Pi with actual hardware")
    print("3. Add known faces using the face recognition system")
    print("4. Test configuration queue: python config_demo.py")
    print("5. Run the main system: python main.py")

if __name__ == "__main__":
    main()
