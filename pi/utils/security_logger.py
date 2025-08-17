"""
Security Logging Utilities
Handles logging and alerting for security events
"""

import os
import json
from datetime import datetime
from config.settings import Settings

class SecurityLogger:
    """Handles security event logging and alerts"""
    
    def __init__(self):
        """Initialize security logger"""
        self.file_paths = Settings.get_file_paths()
        self.log_dir = os.path.join(self.file_paths['captures'], 'logs')
        self.ensure_log_directory()
        
    def ensure_log_directory(self):
        """Ensure log directory exists"""
        try:
            os.makedirs(self.log_dir, exist_ok=True)
        except Exception as e:
            print(f"Warning: Could not create log directory: {e}")
    
    def log_security_event(self, event_type, details, severity='INFO'):
        """
        Log a security event
        
        Args:
            event_type: Type of event (dwelling, unknown_person, etc.)
            details: Event details dict
            severity: Event severity (INFO, WARNING, ALERT)
        """
        timestamp = datetime.now().isoformat()
        log_entry = {
            'timestamp': timestamp,
            'event_type': event_type,
            'severity': severity,
            'details': details
        }
        
        # Log to file
        self._write_to_log_file(log_entry)
        
        # Print alert based on severity
        self._print_alert(log_entry)
        
        return log_entry
    
    def _write_to_log_file(self, log_entry):
        """Write log entry to file"""
        try:
            log_file = os.path.join(self.log_dir, f"security_{datetime.now().strftime('%Y%m%d')}.log")
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
        except Exception as e:
            print(f"Warning: Could not write to log file: {e}")
    
    def _print_alert(self, log_entry):
        """Print alert to console"""
        severity = log_entry['severity']
        event_type = log_entry['event_type']
        timestamp = log_entry['timestamp']
        
        if severity == 'ALERT':
            print(f"\n🚨 SECURITY ALERT 🚨")
            print(f"Time: {timestamp}")
            print(f"Event: {event_type}")
            print(f"Details: {log_entry['details']}")
            print("=" * 50)
        elif severity == 'WARNING':
            print(f"\n⚠️  Security Warning: {event_type} at {timestamp}")
            print(f"Details: {log_entry['details']}")
        else:
            print(f"ℹ️  Security Info: {event_type} at {timestamp}")
    
    def log_dwelling_event(self, dwelling_analysis, known_people, unknown_people):
        """Log dwelling detection event"""
        event_details = {
            'dwelling_detected': dwelling_analysis['dwelling_detected'],
            'confidence': dwelling_analysis['confidence'],
            'duration': dwelling_analysis.get('longest_continuous_presence', 0),
            'people_count': dwelling_analysis.get('average_people_count', 0),
            'known_people': len(known_people),
            'unknown_people': len(unknown_people),
            'message': dwelling_analysis['message']
        }
        
        # Determine severity
        if dwelling_analysis['dwelling_detected'] and unknown_people:
            severity = 'ALERT'
            event_type = 'unknown_person_dwelling'
        elif dwelling_analysis['dwelling_detected']:
            severity = 'WARNING'
            event_type = 'known_person_dwelling'
        else:
            severity = 'INFO'
            event_type = 'person_detected'
        
        return self.log_security_event(event_type, event_details, severity)
    
    def log_face_recognition_event(self, face_analysis):
        """Log face recognition event"""
        event_details = {
            'faces_detected': face_analysis.get('faces_detected', 0),
            'recognized_faces': face_analysis.get('recognized_faces', []),
            'unknown_faces': face_analysis.get('unknown_faces', 0),
            'threat_level': face_analysis.get('threat_level', 'LOW')
        }
        
        severity = 'WARNING' if event_details['unknown_faces'] > 0 else 'INFO'
        event_type = 'face_recognition_analysis'
        
        return self.log_security_event(event_type, event_details, severity)
