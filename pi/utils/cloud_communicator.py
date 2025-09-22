"""
Cloud Communication Module
Handles communication between Pi and cloud infrastructure
"""

import requests
import json
import time
import queue
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
import os
import uuid

class CloudCommunicator:
    """Handles all communication with the cloud API"""
    
    def __init__(self, cloud_url: str, device_id: str, api_key: str):
        """
        Initialize cloud communicator
        
        Args:
            cloud_url: Base URL of cloud API (e.g., "https://api.example.com")
            device_id: Unique device identifier
            api_key: API key for authentication
        """
        self.cloud_url = cloud_url.rstrip('/')
        self.device_id = device_id
        self.api_key = api_key
        
        # Request configuration
        self.timeout = 30  # seconds
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
        # Event queue for offline scenarios
        self.event_queue = queue.Queue(maxsize=100)
        self.queue_thread = None
        self.is_running = False
        
        # Settings cache
        self.cached_settings = {}
        self.last_settings_update = None
        
        # Statistics
        self.stats = {
            'events_sent': 0,
            'events_failed': 0,
            'settings_synced': 0,
            'last_connection': None
        }
        
        print(f"🌐 Cloud communicator initialized for device: {device_id}")
    
    def start(self):
        """Start the cloud communication service"""
        self.is_running = True
        
        # Start background queue processor
        self.queue_thread = threading.Thread(target=self._process_event_queue, daemon=True)
        self.queue_thread.start()
        
        # Initial settings sync
        self._sync_settings_async()
        
        print("🚀 Cloud communication service started")
    
    def stop(self):
        """Stop the cloud communication service"""
        self.is_running = False
        if self.queue_thread:
            self.queue_thread.join(timeout=5)
        print("🛑 Cloud communication service stopped")
    
    def send_security_event(
        self, 
        event_type: str,
        confidence_score: float,
        detected_objects: List[Dict],
        face_analysis: Dict,
        dwelling_analysis: Dict,
        snapshot_path: str,
        video_path: Optional[str] = None,
        priority: bool = False
    ) -> bool:
        """
        Send security event to cloud
        
        Args:
            event_type: Type of event (person_detected, motion, dwelling_alert, etc.)
            confidence_score: Overall confidence of detection
            detected_objects: List of YOLO detected objects
            face_analysis: Face recognition results
            dwelling_analysis: Behavior analysis results
            snapshot_path: Path to snapshot image
            video_path: Path to video file (optional)
            priority: Whether this is a high-priority event
            
        Returns:
            bool: True if sent successfully, False if queued for retry
        """
        event_data = {
            'event_type': event_type,
            'confidence_score': confidence_score,
            'detected_objects': json.dumps(detected_objects),
            'face_analysis': json.dumps(face_analysis),
            'dwelling_analysis': json.dumps(dwelling_analysis),
            'detected_at': datetime.now().isoformat(),
            'device_id': self.device_id,
            'priority': priority
        }
        
        files = {}
        
        # Prepare image file
        if snapshot_path and os.path.exists(snapshot_path):
            files['image'] = ('snapshot.jpg', open(snapshot_path, 'rb'), 'image/jpeg')
        else:
            print(f"⚠️  Snapshot file not found: {snapshot_path}")
            return False
        
        # Prepare video file if available
        if video_path and os.path.exists(video_path):
            files['video'] = ('video.mp4', open(video_path, 'rb'), 'video/mp4')
        
        try:
            # Try to send immediately if high priority
            if priority:
                success = self._send_event_direct(event_data, files)
                if success:
                    print(f"✅ Priority event sent to cloud: {event_type}")
                    return True
            
            # Queue for background processing
            event_item = {
                'data': event_data,
                'files': files,
                'timestamp': time.time(),
                'retries': 0
            }
            
            try:
                self.event_queue.put(event_item, timeout=1)
                print(f"📤 Event queued for cloud: {event_type}")
                return True
            except queue.Full:
                print("❌ Event queue full, dropping event")
                self._close_files(files)
                return False
                
        except Exception as e:
            print(f"❌ Error preparing event for cloud: {e}")
            self._close_files(files)
            return False
    
    def _send_event_direct(self, event_data: Dict, files: Dict) -> bool:
        """Send event directly to cloud API"""
        url = f"{self.cloud_url}/api/v1/events"
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        try:
            response = requests.post(
                url,
                data=event_data,
                files=files,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.stats['events_sent'] += 1
                self.stats['last_connection'] = datetime.now()
                result = response.json()
                print(f"✅ Event sent to cloud - ID: {result.get('event_id', 'unknown')}")
                return True
            else:
                print(f"❌ Cloud API error: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error sending to cloud: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error sending to cloud: {e}")
            return False
        finally:
            self._close_files(files)
    
    def _process_event_queue(self):
        """Background thread to process queued events"""
        while self.is_running:
            try:
                # Get event from queue
                event_item = self.event_queue.get(timeout=1)
                
                # Try to send
                success = self._send_event_direct(event_item['data'], event_item['files'])
                
                if not success:
                    event_item['retries'] += 1
                    
                    # Retry if under limit
                    if event_item['retries'] < self.max_retries:
                        # Wait and requeue
                        time.sleep(self.retry_delay)
                        try:
                            self.event_queue.put(event_item, timeout=1)
                        except queue.Full:
                            print("❌ Queue full during retry, dropping event")
                            self._close_files(event_item['files'])
                    else:
                        print(f"❌ Event failed after {self.max_retries} retries, dropping")
                        self.stats['events_failed'] += 1
                        self._close_files(event_item['files'])
                
                self.event_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Error in event queue processor: {e}")
    
    def sync_settings(self) -> Optional[Dict]:
        """
        Synchronously fetch latest settings from cloud
        
        Returns:
            Dict: Settings data or None if failed
        """
        url = f"{self.cloud_url}/api/v1/devices/{self.device_id}/settings"
        headers = {'Authorization': f'Bearer {self.api_key}'}
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                settings = response.json()
                self.cached_settings = settings
                self.last_settings_update = datetime.now()
                self.stats['settings_synced'] += 1
                self.stats['last_connection'] = datetime.now()
                
                print(f"✅ Settings synced from cloud")
                return settings
            else:
                print(f"❌ Settings sync failed: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Network error syncing settings: {e}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error syncing settings: {e}")
            return None
    
    def _sync_settings_async(self):
        """Asynchronously sync settings in background"""
        def sync_worker():
            self.sync_settings()
        
        thread = threading.Thread(target=sync_worker, daemon=True)
        thread.start()
    
    def get_cached_settings(self) -> Dict:
        """Get last cached settings"""
        return self.cached_settings.copy()
    
    def _close_files(self, files: Dict):
        """Close file handles"""
        for file_obj in files.values():
            if hasattr(file_obj, 'close'):
                try:
                    file_obj.close()
                except:
                    pass
            elif isinstance(file_obj, tuple) and len(file_obj) > 1:
                try:
                    file_obj[1].close()  # Close the file handle in tuple
                except:
                    pass
    
    def get_stats(self) -> Dict:
        """Get communication statistics"""
        return self.stats.copy()
    
    def test_connection(self) -> bool:
        """Test connection to cloud API"""
        url = f"{self.cloud_url}/health"
        try:
            response = requests.get(url, timeout=5)
            success = response.status_code == 200
            if success:
                print("✅ Cloud connection test successful")
            else:
                print(f"❌ Cloud connection test failed: {response.status_code}")
            return success
        except Exception as e:
            print(f"❌ Cloud connection test failed: {e}")
            return False


class CloudConfigurationManager:
    """Manages cloud settings synchronization with local ConfigurationQueue"""
    
    def __init__(self, cloud_communicator: CloudCommunicator, config_queue):
        """
        Initialize cloud configuration manager
        
        Args:
            cloud_communicator: CloudCommunicator instance
            config_queue: ConfigurationQueue instance
        """
        self.cloud_comm = cloud_communicator
        self.config_queue = config_queue
        
        # Sync interval (seconds)
        self.sync_interval = 300  # 5 minutes
        
        # Background sync thread
        self.sync_thread = None
        self.is_running = False
        
        print("⚙️  Cloud configuration manager initialized")
    
    def start(self):
        """Start background settings sync"""
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_worker, daemon=True)
        self.sync_thread.start()
        print("🔄 Background settings sync started")
    
    def stop(self):
        """Stop background settings sync"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=5)
        print("🛑 Background settings sync stopped")
    
    def _sync_worker(self):
        """Background worker for periodic settings sync"""
        while self.is_running:
            try:
                # Sync settings from cloud
                settings = self.cloud_comm.sync_settings()
                
                if settings:
                    self._apply_cloud_settings(settings)
                
                # Wait for next sync
                for _ in range(self.sync_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                print(f"❌ Error in settings sync worker: {e}")
                time.sleep(30)  # Wait before retrying
    
    def _apply_cloud_settings(self, settings: Dict):
        """Apply settings from cloud to local configuration"""
        try:
            # Detection sensitivity
            if 'detection_sensitivity' in settings:
                sensitivity = settings['detection_sensitivity']
                self.config_queue.update_yolo_confidence(sensitivity, priority=2)
                print(f"🎯 Updated detection sensitivity: {sensitivity}")
            
            # Notification preferences
            if 'notification_preferences' in settings:
                prefs = settings['notification_preferences']
                # These would be used by the evaluation logic
                print(f"📱 Updated notification preferences: {prefs}")
            
            # Face embeddings (trusted users)
            if 'face_embeddings' in settings:
                embeddings = settings['face_embeddings']
                for face_data in embeddings:
                    name = face_data.get('name')
                    embedding = face_data.get('embedding')
                    
                    if name and embedding:
                        # Add to face recognition system
                        self.config_queue.add_trusted_person(
                            name, 
                            json.dumps(embedding).encode(),  # Convert to bytes
                            priority=2
                        )
                        print(f"👤 Updated trusted face: {name}")
            
            print("✅ Cloud settings applied successfully")
            
        except Exception as e:
            print(f"❌ Error applying cloud settings: {e}")
    
    def force_sync(self):
        """Force immediate settings sync"""
        settings = self.cloud_comm.sync_settings()
        if settings:
            self._apply_cloud_settings(settings)
            return True
        return False
