import json
import tempfile
import unittest
from pathlib import Path

from pi.utils.security_logger import SecurityLogger


class SecurityLoggerTests(unittest.TestCase):
    def test_dwelling_log_accepts_counts_from_orchestrator(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = SecurityLogger(log_dir=directory)
            entry = logger.log_dwelling_event(
                {
                    "dwelling_detected": True,
                    "confidence": 0.91,
                    "message": "Unknown person remained in view",
                },
                known_people=0,
                unknown_people=1,
            )

            self.assertEqual(entry["event_type"], "unknown_person_dwelling")
            self.assertEqual(entry["severity"], "ALERT")
            self.assertEqual(entry["details"]["unknown_people"], 1)

            log_files = list(Path(directory).glob("security_*.log"))
            self.assertEqual(len(log_files), 1)
            persisted = json.loads(log_files[0].read_text().strip())
            self.assertEqual(persisted["event_type"], "unknown_person_dwelling")

    def test_face_log_matches_face_recognition_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            logger = SecurityLogger(log_dir=directory)
            entry = logger.log_face_recognition_event(
                {
                    "total_faces": 2,
                    "known_faces": 1,
                    "unknown_faces": 1,
                    "threat_detected": True,
                }
            )

            self.assertEqual(entry["severity"], "WARNING")
            self.assertEqual(entry["details"]["faces_detected"], 2)
            self.assertEqual(entry["details"]["recognized_faces"], 1)


if __name__ == "__main__":
    unittest.main()
