import unittest

from pi.event_policy import classify_event, split_faces


class EventPolicyTests(unittest.TestCase):
    def test_unknown_face_is_uploaded(self):
        faces = {"faces": [{"recognized": False, "person_name": "Unknown"}]}
        decision = classify_event({"dwelling_detected": False}, faces)
        self.assertTrue(decision.should_upload)
        self.assertEqual(decision.event_type, "unknown_person_detected")
        self.assertFalse(decision.priority)

    def test_unknown_dwelling_event_is_priority(self):
        faces = {"faces": [{"recognized": False}]}
        decision = classify_event({"dwelling_detected": True}, faces)
        self.assertEqual(decision.event_type, "dwelling_alert_unknown")
        self.assertTrue(decision.priority)

    def test_brief_known_person_stays_on_device(self):
        faces = {"faces": [{"recognized": True, "person_name": "Resident"}]}
        decision = classify_event({"dwelling_detected": False}, faces)
        self.assertFalse(decision.should_upload)
        self.assertEqual(decision.event_type, "known_person_detected")

    def test_long_known_person_event_is_uploaded(self):
        faces = {"faces": [{"recognized": True}]}
        dwelling = {"dwelling_detected": True, "longest_continuous_presence": 61}
        decision = classify_event(dwelling, faces)
        self.assertTrue(decision.should_upload)
        self.assertEqual(decision.event_type, "dwelling_known_person")

    def test_split_faces_preserves_records(self):
        known, unknown = split_faces(
            {
                "faces": [
                    {"recognized": True, "person_name": "Resident"},
                    {"recognized": False, "person_name": "Unknown"},
                ]
            }
        )
        self.assertEqual([face["person_name"] for face in known], ["Resident"])
        self.assertEqual([face["person_name"] for face in unknown], ["Unknown"])


if __name__ == "__main__":
    unittest.main()
