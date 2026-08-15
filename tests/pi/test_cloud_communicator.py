import tempfile
import unittest
from pathlib import Path

from pi.utils.cloud_communicator import CloudCommunicator, CloudConfigurationManager


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = "test response"

    def json(self):
        return self._payload


class FakeSession:
    def __init__(self, post_statuses):
        self.post_statuses = iter(post_statuses)
        self.handles_open_during_post = []

    def post(self, _url, *, files, **_kwargs):
        self.handles_open_during_post.append(
            all(not upload[1].closed for upload in files.values())
        )
        return FakeResponse(next(self.post_statuses), {"event_id": "event-1"})

    def get(self, _url, **_kwargs):
        return FakeResponse(200, {"status": "healthy"})


class CloudCommunicatorTests(unittest.TestCase):
    def make_communicator(self, session):
        return CloudCommunicator(
            "https://camera.example",
            "pi-1",
            "device-token",
            retry_delay=0,
            session=session,
        )

    def test_requires_complete_device_configuration(self):
        with self.assertRaises(ValueError):
            CloudCommunicator("https://camera.example", "pi-1", "")

    def test_nonpriority_event_queues_paths_without_open_handles(self):
        session = FakeSession([201])
        communicator = self.make_communicator(session)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot.jpg"
            snapshot.write_bytes(b"image")
            queued = communicator.send_security_event(
                "unknown_person_detected", 0.9, [], {}, {}, str(snapshot)
            )
            self.assertTrue(queued)
            item = communicator.event_queue.get_nowait()
            self.assertEqual(item["snapshot_path"], snapshot)
            self.assertIsInstance(item["snapshot_path"], Path)

    def test_retry_reopens_media_files(self):
        session = FakeSession([500, 201])
        communicator = self.make_communicator(session)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot.jpg"
            snapshot.write_bytes(b"image")
            queued = communicator.send_security_event(
                "dwelling_alert_unknown", 0.9, [], {}, {}, str(snapshot), priority=True
            )
            self.assertTrue(queued)
            item = communicator.event_queue.get_nowait()
            sent = communicator._send_event_direct(
                item["data"], item["snapshot_path"], item["video_path"]
            )
            self.assertTrue(sent)
            self.assertEqual(session.handles_open_during_post, [True, True])

    def test_successful_priority_event_is_not_queued(self):
        session = FakeSession([201])
        communicator = self.make_communicator(session)
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "snapshot.jpg"
            snapshot.write_bytes(b"image")
            sent = communicator.send_security_event(
                "dwelling_alert_unknown", 0.9, [], {}, {}, str(snapshot), priority=True
            )
            self.assertTrue(sent)
            self.assertTrue(communicator.event_queue.empty())

    def test_cloud_face_embeddings_use_embedding_queue_path(self):
        calls = []

        class FakeConfigQueue:
            def add_trusted_embedding(self, *args, **kwargs):
                calls.append((args, kwargs))

        manager = CloudConfigurationManager(
            self.make_communicator(FakeSession([])), FakeConfigQueue()
        )
        manager._apply_cloud_settings(
            {
                "face_embeddings": [
                    {"id": 7, "name": "Resident", "embedding": [0.0] * 128}
                ]
            }
        )

        self.assertEqual(calls[0][0][0], "Resident")
        self.assertEqual(calls[0][1]["person_id"], "cloud_7")


if __name__ == "__main__":
    unittest.main()
