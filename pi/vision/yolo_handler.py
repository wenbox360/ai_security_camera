"""
YOLO Object Detection Handler
Handles YOLO result processing
"""

import time
from ultralytics import YOLO 
from config.settings import Settings

class YOLOHandler:
    """Handles YOLO object detection results"""
    
    def __init__(self):
        """Initialize YOLO model"""
        self.model = YOLO(Settings.get_yolo_model())
        print(f"YOLO model loaded from {Settings.get_yolo_model()}")

    def process_frame(self, frame):
        """Process a single frame for object detection"""
        results = self.model(frame)
        
        # Extract comprehensive detections
        detections = []
        for result in results:
            for box in result.boxes:
                # Get box coordinates in different formats
                xyxy = box.xyxy.tolist()[0]  # [x1, y1, x2, y2]
                xywh = box.xywh.tolist()[0]  # [center_x, center_y, width, height]
                
                detection = {
                    # Basic detection info
                    'class_id': int(box.cls),
                    'class_name': result.names[int(box.cls)],
                    'confidence': float(box.conf),
                    
                    # Bounding box in different formats
                    'bbox_xyxy': xyxy,  # [x1, y1, x2, y2]
                    'bbox_xywh': xywh,  # [center_x, center_y, width, height]
                    'bbox_normalized': box.xyxyn.tolist()[0],  # Normalized coordinates
                    
                    # Object size info
                    'width': xyxy[2] - xyxy[0],
                    'height': xyxy[3] - xyxy[1],
                    'area': (xyxy[2] - xyxy[0]) * (xyxy[3] - xyxy[1]),
                    
                    # Tracking ID (if available)
                    'track_id': int(box.id) if box.id is not None else None,
                }
                
                detections.append(detection)
        
        # Add result metadata
        result_info = {
            'detections': detections,
            'total_objects': len(detections),
            'image_shape': results[0].orig_shape if results else None,
            'inference_time': getattr(results[0], 'speed', {}).get('inference', 0) if results else 0,
            'timestamp': time.time()
        }
        
        return result_info
    
    def get_detection_summary(self, result_info):
        """Get summary of detected objects"""
        detections = result_info['detections']
        
        # Count objects by class
        class_counts = {}
        for detection in detections:
            class_name = detection['class_name']
            class_counts[class_name] = class_counts.get(class_name, 0) + 1
        
        return {
            'total_objects': len(detections),
            'class_counts': class_counts,
            'has_person': any(d['class_name'] == 'person' for d in detections),
            'has_vehicle': any(d['class_name'] in ['car', 'truck', 'van', 'motorcycle'] for d in detections),
            'highest_confidence': max((d['confidence'] for d in detections), default=0),
            'inference_time': result_info['inference_time']
        }
    
    def filter_detections(self, result_info, min_confidence=0.5, classes_of_interest=None):
        """Filter detections by confidence and classes"""
        detections = result_info['detections']
        
        filtered = []
        for detection in detections:
            # Filter by confidence
            if detection['confidence'] < min_confidence:
                continue
                
            # Filter by classes of interest
            if classes_of_interest and detection['class_name'] not in classes_of_interest:
                continue
                
            filtered.append(detection)
        
        result_info['detections'] = filtered
        result_info['total_objects'] = len(filtered)
        
        return result_info