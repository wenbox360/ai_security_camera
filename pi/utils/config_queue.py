"""
Configuration Queue System
Handles configuration updates while system is busy processing
Acts like a REST API queue for POST requests
"""

import queue
import threading
import time
import json
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

class ConfigAction(Enum):
    """Configuration action types"""
    UPDATE_YOLO_CONFIG = "update_yolo_config"
    ADD_TRUSTED_FACE = "add_trusted_face"
    REMOVE_TRUSTED_FACE = "remove_trusted_face"
    UPDATE_DWELLING_CONFIG = "update_dwelling_config"
    UPDATE_CAMERA_CONFIG = "update_camera_config"

@dataclass
class ConfigRequest:
    """Configuration request data structure"""
    action: ConfigAction
    data: Dict[str, Any]
    request_id: str
    timestamp: str
    priority: int = 1  # 1=high, 2=medium, 3=low
    
    def __lt__(self, other):
        """Make ConfigRequest comparable for priority queue"""
        if isinstance(other, ConfigRequest):
            return self.priority < other.priority
        return NotImplemented

class ConfigurationQueue:
    """Queue system for handling configuration updates"""
    
    def __init__(self, security_system=None):
        """Initialize configuration queue"""
        self.security_system = security_system
        
        # Configuration queue with priority
        self.config_queue = queue.PriorityQueue(maxsize=50)
        
        # Processing state
        self.is_processing = False
        self.processor_thread = None
        self.request_counter = 0
        
        # Results tracking
        self.completed_requests = {}
        self.failed_requests = {}
        
        # Start processing thread
        self.start_processor()
    
    def start_processor(self):
        """Start the configuration processor thread"""
        self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processor_thread.start()
        print("📋 Configuration queue processor started")
    
    def add_request(self, action: ConfigAction, data: Dict[str, Any], priority: int = 1) -> str:
        """
        Add a configuration request to the queue
        
        Args:
            action: Type of configuration action
            data: Configuration data
            priority: Request priority (1=high, 2=medium, 3=low)
            
        Returns:
            str: Request ID for tracking
        """
        self.request_counter += 1
        request_id = f"cfg_{self.request_counter}_{int(time.time())}"
        
        config_request = ConfigRequest(
            action=action,
            data=data,
            request_id=request_id,
            timestamp=datetime.now().isoformat(),
            priority=priority
        )
        
        try:
            # Add to priority queue (lower number = higher priority)
            self.config_queue.put((priority, config_request), timeout=1)
            print(f"📥 Config request queued: {action.value} (ID: {request_id})")
            return request_id
            
        except queue.Full:
            print(f"❌ Configuration queue full, request rejected: {action.value}")
            return None
    
    def _process_queue(self):
        """Process configuration requests from queue"""
        while True:
            try:
                # Get next request (blocks until available)
                priority, config_request = self.config_queue.get(timeout=1)
                
                self.is_processing = True
                print(f"🔧 Processing config request: {config_request.action.value} (ID: {config_request.request_id})")
                
                # Process the request
                success, result = self._execute_config_request(config_request)
                
                # Store result
                if success:
                    self.completed_requests[config_request.request_id] = {
                        'action': config_request.action.value,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    print(f"✅ Config request completed: {config_request.request_id}")
                else:
                    self.failed_requests[config_request.request_id] = {
                        'action': config_request.action.value,
                        'error': result,
                        'timestamp': datetime.now().isoformat()
                    }
                    print(f"❌ Config request failed: {config_request.request_id} - {result}")
                
                # Mark task as done
                self.config_queue.task_done()
                self.is_processing = False
                
                # Small delay between requests
                time.sleep(0.1)
                
            except queue.Empty:
                # No requests to process
                self.is_processing = False
                continue
            except Exception as e:
                print(f"❌ Config processor error: {e}")
                self.is_processing = False
    
    def _execute_config_request(self, request: ConfigRequest) -> tuple[bool, str]:
        """
        Execute a configuration request
        
        Returns:
            tuple: (success, result_or_error_message)
        """
        try:
            action = request.action
            data = request.data
            
            if action == ConfigAction.UPDATE_YOLO_CONFIG:
                return self._update_yolo_config(data)
            
            elif action == ConfigAction.ADD_TRUSTED_FACE:
                return self._add_trusted_face(data)
            
            elif action == ConfigAction.REMOVE_TRUSTED_FACE:
                return self._remove_trusted_face(data)
            
            elif action == ConfigAction.UPDATE_DWELLING_CONFIG:
                return self._update_dwelling_config(data)
            
            elif action == ConfigAction.UPDATE_CAMERA_CONFIG:
                return self._update_camera_config(data)
            
            else:
                return False, f"Unknown action: {action.value}"
                
        except Exception as e:
            return False, f"Execution error: {str(e)}"
    
    def _update_yolo_config(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Update YOLO configuration"""
        try:
            yolo_handler = self.security_system.yolo_handler if self.security_system else None
            
            if not yolo_handler:
                return False, "YOLO handler not available"
            
            # Update confidence threshold
            if 'min_confidence' in data:
                new_confidence = float(data['min_confidence'])
                if 0.0 <= new_confidence <= 1.0:
                    # Update in behavior analyzer
                    if self.security_system.behavior_analyzer:
                        self.security_system.behavior_analyzer.min_confidence = new_confidence
                    result = f"YOLO confidence updated to {new_confidence}"
                else:
                    return False, "Confidence must be between 0.0 and 1.0"
            
            # Update model path (requires reload)
            if 'model_path' in data:
                model_path = data['model_path']
                # This would require reloading the YOLO model
                # For now, just validate the path
                import os
                if os.path.exists(model_path):
                    result = f"YOLO model path validated: {model_path} (restart required)"
                else:
                    return False, f"Model file not found: {model_path}"
            
            return True, result
            
        except Exception as e:
            return False, f"YOLO config update failed: {str(e)}"
    
    def _add_trusted_face(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Add trusted face to face recognition system"""
        try:
            face_handler = self.security_system.face_recognition if self.security_system else None
            
            if not face_handler:
                return False, "Face recognition handler not available"
            
            # Required fields
            if 'name' not in data or 'image_data' not in data:
                return False, "Missing required fields: name, image_data"
            
            name = data['name']
            image_data = data['image_data']  # Base64 encoded or bytes
            
            # Store the face
            success = face_handler.store_face_from_image(image_data, name)
            
            if success:
                return True, f"Trusted face added: {name}"
            else:
                return False, f"Failed to add face: {name}"
                
        except Exception as e:
            return False, f"Add trusted face failed: {str(e)}"
    
    def _remove_trusted_face(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Remove trusted face from face recognition system"""
        try:
            face_handler = self.security_system.face_recognition if self.security_system else None
            
            if not face_handler:
                return False, "Face recognition handler not available"
            
            if 'name' not in data:
                return False, "Missing required field: name"
            
            name = data['name']
            
            # Load current faces
            import os
            import json
            
            if hasattr(face_handler, 'known_faces_file'):
                faces_file = face_handler.known_faces_file
                
                if os.path.exists(faces_file):
                    with open(faces_file, 'r') as f:
                        known_faces = json.load(f)
                    
                    # Remove the face
                    if name in known_faces:
                        del known_faces[name]
                        
                        # Save updated faces
                        with open(faces_file, 'w') as f:
                            json.dump(known_faces, f, indent=2)
                        
                        # Reload in memory
                        face_handler._load_known_faces()
                        
                        return True, f"Trusted face removed: {name}"
                    else:
                        return False, f"Face not found: {name}"
                else:
                    return False, "No trusted faces database found"
            else:
                return False, "Face handler not properly configured"
                
        except Exception as e:
            return False, f"Remove trusted face failed: {str(e)}"
    
    def _update_dwelling_config(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Update dwelling detection configuration"""
        try:
            analyzer = self.security_system.behavior_analyzer if self.security_system else None
            
            if not analyzer:
                return False, "Behavior analyzer not available"
            
            results = []
            
            # Update dwelling threshold
            if 'dwelling_threshold' in data:
                threshold = float(data['dwelling_threshold'])
                if threshold > 0:
                    analyzer.dwelling_threshold = threshold
                    results.append(f"dwelling_threshold={threshold}s")
                else:
                    return False, "Dwelling threshold must be positive"
            
            # Update frame skip
            if 'frame_skip' in data:
                frame_skip = int(data['frame_skip'])
                if frame_skip > 0:
                    analyzer.frame_skip = frame_skip
                    results.append(f"frame_skip={frame_skip}")
                else:
                    return False, "Frame skip must be positive"
            
            return True, f"Dwelling config updated: {', '.join(results)}"
            
        except Exception as e:
            return False, f"Dwelling config update failed: {str(e)}"
    
    def _update_camera_config(self, data: Dict[str, Any]) -> tuple[bool, str]:
        """Update camera configuration"""
        try:
            camera = self.security_system.camera_manager if self.security_system else None
            
            if not camera:
                return False, "Camera manager not available"
            
            results = []
            
            # Update video duration
            if 'video_duration' in data:
                duration = float(data['video_duration'])
                if duration > 0:
                    camera.video_settings['duration'] = duration
                    results.append(f"video_duration={duration}s")
                else:
                    return False, "Video duration must be positive"
            
            # Note: Some camera settings may require restart
            return True, f"Camera config updated: {', '.join(results)} (may require restart)"
            
        except Exception as e:
            return False, f"Camera config update failed: {str(e)}"
    
    # API-like methods for external use
    def update_yolo_confidence(self, confidence: float, priority: int = 1) -> str:
        """API method to update YOLO confidence"""
        return self.add_request(
            ConfigAction.UPDATE_YOLO_CONFIG,
            {'min_confidence': confidence},
            priority
        )
    
    def add_trusted_person(self, name: str, image_data: bytes, priority: int = 1) -> str:
        """API method to add trusted person"""
        return self.add_request(
            ConfigAction.ADD_TRUSTED_FACE,
            {'name': name, 'image_data': image_data},
            priority
        )
    
    def remove_trusted_person(self, name: str, priority: int = 1) -> str:
        """API method to remove trusted person"""
        return self.add_request(
            ConfigAction.REMOVE_TRUSTED_FACE,
            {'name': name},
            priority
        )
    
    def update_dwelling_threshold(self, threshold: float, priority: int = 1) -> str:
        """API method to update dwelling threshold"""
        return self.add_request(
            ConfigAction.UPDATE_DWELLING_CONFIG,
            {'dwelling_threshold': threshold},
            priority
        )
    
    def get_request_status(self, request_id: str) -> Dict[str, Any]:
        """Get status of a configuration request"""
        if request_id in self.completed_requests:
            return {
                'status': 'completed',
                'result': self.completed_requests[request_id]
            }
        elif request_id in self.failed_requests:
            return {
                'status': 'failed',
                'error': self.failed_requests[request_id]
            }
        else:
            return {
                'status': 'pending_or_not_found'
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            'queue_size': self.config_queue.qsize(),
            'is_processing': self.is_processing,
            'completed_requests': len(self.completed_requests),
            'failed_requests': len(self.failed_requests)
        }
    
    def cleanup(self):
        """Clean up the configuration queue"""
        # Wait for current processing to finish
        if self.is_processing:
            print("⏳ Waiting for current config request to finish...")
            time.sleep(2)
        
        print("🧹 Configuration queue cleaned up")
