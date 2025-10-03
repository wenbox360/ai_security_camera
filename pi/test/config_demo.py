"""
Configuration Queue Example Usage
Demonstrates how to use the configuration queue for system updates
"""

import sys
import os
import time
import base64

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import SecurityCameraSystem
from utils.config_queue import ConfigAction

def example_usage():
    """Example of using the configuration queue"""
    
    print("🔧 Configuration Queue Example")
    print("=" * 40)
    
    # Create and initialize security system
    security_system = SecurityCameraSystem()
    
    # Initialize the system (this will create the config queue)
    if not security_system.initialize_system():
        print("❌ Failed to initialize system")
        return
    
    print("\n📋 Configuration Queue Features:")
    print("1. Update YOLO confidence threshold")
    print("2. Add/Remove trusted people")
    print("3. Update dwelling detection settings")
    print("4. Priority-based request processing")
    print("5. Non-blocking queue operations")
    
    # Example 1: Update YOLO confidence
    print("\n🎯 Example 1: Update YOLO Confidence")
    request_id = security_system.update_yolo_confidence(0.7, priority=1)
    print(f"   Request ID: {request_id}")
    
    # Wait and check status
    time.sleep(0.5)
    status = security_system.get_config_request_status(request_id)
    print(f"   Status: {status}")
    
    # Example 2: Update dwelling threshold  
    print("\n🏠 Example 2: Update Dwelling Threshold")
    request_id = security_system.update_dwelling_threshold(15.0, priority=2)
    print(f"   Request ID: {request_id}")
    
    time.sleep(0.5)
    status = security_system.get_config_request_status(request_id)
    print(f"   Status: {status}")
    
    # Example 3: Add trusted person (simulated image data)
    print("\n👤 Example 3: Add Trusted Person")
    # In real usage, this would be actual image bytes from uploaded file
    fake_image_data = base64.b64encode(b"fake_image_data_here").decode()
    request_id = security_system.add_trusted_person("John Doe", fake_image_data.encode(), priority=1)
    print(f"   Request ID: {request_id}")
    
    time.sleep(0.5)
    status = security_system.get_config_request_status(request_id)
    print(f"   Status: {status}")
    
    # Example 4: Queue multiple requests
    print("\n🔄 Example 4: Multiple Requests")
    requests = []
    
    # Queue several requests with different priorities
    requests.append(security_system.update_yolo_confidence(0.8, priority=3))  # Low priority
    requests.append(security_system.update_dwelling_threshold(10.0, priority=1))  # High priority
    requests.append(security_system.update_yolo_confidence(0.9, priority=2))  # Medium priority
    
    print(f"   Queued {len(requests)} requests with different priorities")
    
    # Wait for processing
    time.sleep(2)
    
    # Check all statuses
    for i, req_id in enumerate(requests):
        status = security_system.get_config_request_status(req_id)
        print(f"   Request {i+1}: {status['status']}")
    
    # Example 5: Check queue status
    print("\n📊 Example 5: Queue Status")
    queue_status = security_system.get_system_status()['config_queue']
    print(f"   Queue Size: {queue_status['queue_size']}")
    print(f"   Processing: {queue_status['is_processing']}")
    print(f"   Completed: {queue_status['completed_requests']}")
    print(f"   Failed: {queue_status['failed_requests']}")
    
    print("\n✅ Configuration queue examples completed!")
    
    # Cleanup
    security_system.shutdown_system()

def simulate_rest_api_usage():
    """Simulate how this would be used with a REST API"""
    
    print("\n🌐 REST API Simulation")
    print("=" * 40)
    
    # This simulates what would happen when receiving POST requests
    
    # POST /api/config/yolo
    def post_yolo_config(confidence):
        print(f"POST /api/config/yolo - confidence: {confidence}")
        # In real API, security_system would be a global instance
        # request_id = security_system.update_yolo_confidence(confidence)
        # return {"request_id": request_id, "status": "queued"}
        return {"request_id": "cfg_123_456", "status": "queued"}
    
    # POST /api/config/trusted-faces
    def post_trusted_face(name, image_file):
        print(f"POST /api/config/trusted-faces - name: {name}")
        # In real API:
        # image_data = image_file.read()
        # request_id = security_system.add_trusted_person(name, image_data)
        # return {"request_id": request_id, "status": "queued"}
        return {"request_id": "cfg_124_457", "status": "queued"}
    
    # DELETE /api/config/trusted-faces/{name}
    def delete_trusted_face(name):
        print(f"DELETE /api/config/trusted-faces/{name}")
        # In real API:
        # request_id = security_system.remove_trusted_person(name)
        # return {"request_id": request_id, "status": "queued"}
        return {"request_id": "cfg_125_458", "status": "queued"}
    
    # GET /api/config/requests/{request_id}
    def get_request_status(request_id):
        print(f"GET /api/config/requests/{request_id}")
        # In real API:
        # return security_system.get_config_request_status(request_id)
        return {"status": "completed", "result": {"action": "update_yolo_config"}}
    
    # Simulate API calls
    print("Simulating API endpoints:")
    print(post_yolo_config(0.75))
    print(post_trusted_face("Alice", "image_file"))
    print(delete_trusted_face("Bob"))
    print(get_request_status("cfg_123_456"))

if __name__ == "__main__":
    print("🚀 Configuration Queue Demo")
    
    try:
        # Run examples
        example_usage()
        simulate_rest_api_usage()
        
    except KeyboardInterrupt:
        print("\n⏹️  Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo error: {e}")
    
    print("\n👋 Demo completed!")
