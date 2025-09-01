"""
Face Recognition Handler
Compares detected faces against known face embeddings stored locally
"""

import json
import os
import numpy as np
import cv2
from datetime import datetime
import face_recognition  # pip install face-recognition
from config.settings import Settings

class FaceRecognitionHandler:
    """Handles face recognition using local embedding storage"""
    
    def __init__(self):
        """Initialize face recognition with local storage"""
        self.embeddings_file = Settings.get_face_embeddings_path()
        self.face_images_dir = Settings.get_face_images_dir()
        self.metadata_file = Settings.get_face_metadata_path()
        
        # Load known faces from local storage
        self.known_faces = self.load_known_faces()
        print(f"Loaded {len(self.known_faces)} known faces")
        
    def load_known_faces(self):
        """Load known face embeddings from local storage"""
        try:
            if os.path.exists(self.embeddings_file):
                with open(self.embeddings_file, 'r') as f:
                    data = json.load(f)
                    
                # Convert embeddings back to numpy arrays
                known_faces = {}
                for person_id, face_data in data.items():
                    embeddings = [np.array(emb) for emb in face_data['embeddings']]
                    known_faces[person_id] = {
                        'name': face_data['name'],
                        'embeddings': embeddings,
                        'created_date': face_data.get('created_date'),
                        'last_seen': face_data.get('last_seen')
                    }
                return known_faces
            else:
                return {}
                
        except Exception as e:
            print(f"Error loading known faces: {e}")
            return {}
    
    def _save_known_faces(self):
        """Save known face embeddings to local storage (internal use only)"""
        try:
            # Convert numpy arrays to lists for JSON serialization
            data = {}
            for person_id, face_data in self.known_faces.items():
                embeddings_list = [emb.tolist() for emb in face_data['embeddings']]
                data[person_id] = {
                    'name': face_data['name'],
                    'embeddings': embeddings_list,
                    'created_date': face_data.get('created_date'),
                    'last_seen': face_data.get('last_seen')
                }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.embeddings_file), exist_ok=True)
            
            # Save to file
            with open(self.embeddings_file, 'w') as f:
                json.dump(data, f, indent=2)
                
            print(f"Saved {len(self.known_faces)} known faces to {self.embeddings_file}")
            
        except Exception as e:
            print(f"Error saving known faces: {e}")
    
    def find_best_match(self, face_encoding, tolerance=0.6):
        """Find the best matching known face"""
        best_match = None
        best_distance = float('inf')
        
        for person_id, face_data in self.known_faces.items():
            for known_encoding in face_data['embeddings']:
                # Calculate face distance (lower = more similar)
                distance = face_recognition.face_distance([known_encoding], face_encoding)[0]
                
                if distance < tolerance and distance < best_distance:
                    best_distance = distance
                    best_match = {
                        'person_id': person_id,
                        'name': face_data['name'],
                        'confidence': 1.0 - distance,  # Convert distance to confidence
                        'distance': distance
                    }
        
        return best_match
    
    def update_last_seen(self, person_id):
        """Update last seen timestamp for a person (in memory only)"""
        if person_id in self.known_faces:
            self.known_faces[person_id]['last_seen'] = datetime.now().isoformat()
            # Note: Not saving to disk - only persistent when new faces are added
    
    def is_face_recognized(self, face_encoding, tolerance=0.6):
        """
        Check if a single face encoding matches any known face
        
        Args:
            face_encoding: Face encoding array from face_recognition
            tolerance: Recognition tolerance (lower = stricter)
            
        Returns:
            dict: Recognition result with person info or None if unknown
        """
        try:
            best_match = self.find_best_match(face_encoding, tolerance)
            
            if best_match:
                # Update last seen
                self.update_last_seen(best_match['person_id'])
                return {
                    'recognized': True,
                    'person_id': best_match['person_id'],
                    'person_name': best_match['name'],
                    'confidence': best_match['confidence'],
                    'distance': best_match['distance']
                }
            else:
                return {
                    'recognized': False,
                    'person_id': 'unknown',
                    'person_name': 'Unknown',
                    'confidence': 0.0,
                    'distance': float('inf')
                }
                
        except Exception as e:
            print(f"Error recognizing face: {e}")
            return {
                'recognized': False,
                'person_id': 'error',
                'person_name': 'Error',
                'confidence': 0.0,
                'distance': float('inf')
            }
    
    def analyze_frame_for_threats(self, frame, tolerance=0.6):
        """
        Analyze camera frame for unknown faces (potential threats)
        
        Args:
            frame: Camera frame (numpy array)
            tolerance: Recognition tolerance
            
        Returns:
            dict: Analysis result with threat assessment
        """
        try:
            # Find all faces in frame
            face_locations = face_recognition.face_locations(frame)
            face_encodings = face_recognition.face_encodings(frame, face_locations)
            
            if not face_encodings:
                return {
                    'threat_detected': False,
                    'total_faces': 0,
                    'known_faces': 0,
                    'unknown_faces': 0,
                    'faces': [],
                    'message': 'No faces detected'
                }
            
            recognized_faces = []
            unknown_count = 0
            known_count = 0
            
            # Check each face
            for i, (location, encoding) in enumerate(zip(face_locations, face_encodings)):
                recognition_result = self.is_face_recognized(encoding, tolerance)
                
                face_info = {
                    'face_id': i,
                    'location': location,  # (top, right, bottom, left)
                    'recognized': recognition_result['recognized'],
                    'person_id': recognition_result['person_id'],
                    'person_name': recognition_result['person_name'],
                    'confidence': recognition_result['confidence']
                }
                
                recognized_faces.append(face_info)
                
                if recognition_result['recognized']:
                    known_count += 1
                else:
                    unknown_count += 1
            
            # Determine threat level
            threat_detected = unknown_count > 0
            
            # Generate message
            if unknown_count > 0 and known_count > 0:
                message = f"Mixed: {known_count} known, {unknown_count} unknown faces"
            elif unknown_count > 0:
                message = f"Threat: {unknown_count} unknown face(s) detected"
            else:
                message = f"Safe: {known_count} known face(s) detected"
            
            return {
                'threat_detected': threat_detected,
                'total_faces': len(face_encodings),
                'known_faces': known_count,
                'unknown_faces': unknown_count,
                'faces': recognized_faces,
                'message': message
            }
            
        except Exception as e:
            print(f"Error analyzing frame for threats: {e}")
            return {
                'threat_detected': True,  # Assume threat on error for safety
                'total_faces': 0,
                'known_faces': 0,
                'unknown_faces': 0,
                'faces': [],
                'message': f'Error analyzing frame: {e}'
            }
    
    def store_face_from_image(self, image_data, person_name, person_id=None):
        """
        Store a face from image data (from backend/upload)
        
        Args:
            image_data: Image data (bytes, numpy array, or file path)
            person_name: Name of the person
            person_id: Optional ID (will generate if not provided)
            
        Returns:
            dict: Storage result with success status
        """
        try:
            # Generate person ID if not provided
            if person_id is None:
                person_id = person_name.lower().replace(' ', '_').replace('-', '_')
                # Add timestamp to avoid conflicts
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                person_id = f"{person_id}_{timestamp}"
            
            # Handle different image data types
            if isinstance(image_data, str):
                # File path
                image = face_recognition.load_image_file(image_data)
            elif isinstance(image_data, bytes):
                # Bytes data (from upload)
                import io
                from PIL import Image
                pil_image = Image.open(io.BytesIO(image_data))
                image = np.array(pil_image)
            elif isinstance(image_data, np.ndarray):
                # Numpy array (camera frame)
                image = image_data
            else:
                return {
                    'success': False,
                    'error': 'Unsupported image data type',
                    'person_id': None
                }
            
            # Extract face encoding
            face_encodings = face_recognition.face_encodings(image)
            
            if not face_encodings:
                return {
                    'success': False,
                    'error': 'No face found in image',
                    'person_id': None
                }
            
            if len(face_encodings) > 1:
                print(f"Warning: Multiple faces found, using the first one")
            
            face_encoding = face_encodings[0]
            
            # Create face data entry
            if person_id not in self.known_faces:
                self.known_faces[person_id] = {
                    'name': person_name,
                    'embeddings': [],
                    'created_date': datetime.now().isoformat(),
                    'last_seen': None
                }
            
            # Add the embedding
            self.known_faces[person_id]['embeddings'].append(face_encoding)
            
            # Save the face image to disk (optional - for reference)
            try:
                os.makedirs(self.face_images_dir, exist_ok=True)
                image_filename = f"{person_id}_{len(self.known_faces[person_id]['embeddings'])}.jpg"
                image_path = os.path.join(self.face_images_dir, image_filename)
                
                if isinstance(image_data, bytes):
                    with open(image_path, 'wb') as f:
                        f.write(image_data)
                else:
                    # Convert and save as JPEG using OpenCV
                    if isinstance(image, np.ndarray):
                        # Convert RGB to BGR for OpenCV if needed
                        if len(image.shape) == 3 and image.shape[2] == 3:
                            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                            cv2.imwrite(image_path, image_bgr)
                        else:
                            cv2.imwrite(image_path, image)
            except Exception as img_save_error:
                print(f"Warning: Could not save reference image: {img_save_error}")
            
            # Save embeddings to disk
            self._save_known_faces()
            
            return {
                'success': True,
                'person_id': person_id,
                'person_name': person_name,
                'embeddings_count': len(self.known_faces[person_id]['embeddings']),
                'message': f'Successfully stored face for {person_name}'
            }
            
        except Exception as e:
            print(f"Error storing face: {e}")
            return {
                'success': False,
                'error': str(e),
                'person_id': None
            }
