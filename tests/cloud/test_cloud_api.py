from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from cloud import main
from cloud.auth import get_device_api_key_hash, get_password_hash
from cloud.database import Base, Device, SecurityEvent, User
from cloud.tasks.llm_analysis import request_analysis


@pytest.fixture()
def api(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_db():
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    main.app.dependency_overrides[main.get_db] = override_db
    monkeypatch.setattr(main, "get_s3_client", lambda: object())
    monkeypatch.setattr(
        main,
        "upload_to_s3",
        lambda file_obj, key, client, bucket: f"s3://{bucket}/{key}",
    )
    monkeypatch.setattr(main, "generate_presigned_url", lambda url, client, bucket: url)
    monkeypatch.setattr(
        main.analyze_security_event,
        "delay",
        lambda event_id: SimpleNamespace(id="analysis-1"),
    )
    try:
        yield TestClient(main.app), session_factory
    finally:
        main.app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_login_event_ingestion_and_owner_scoped_listing(api):
    client, session_factory = api
    session = session_factory()
    try:
        user = User(
            username="owner",
            email="owner@example.test",
            hashed_password=get_password_hash("correct horse"),
        )
        session.add(user)
        session.flush()
        raw_device_key = "device-secret"
        device = Device(
            device_id="front-door",
            name="Front Door",
            owner_id=user.id,
            api_key_hash=get_device_api_key_hash(raw_device_key),
        )
        assert device.api_key_hash != raw_device_key
        assert len(device.api_key_hash) == 64
        session.add(device)
        session.commit()
    finally:
        session.close()

    login = client.post(
        "/api/v1/auth/login", json={"username": "owner", "password": "correct horse"}
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    created = client.post(
        "/api/v1/events",
        headers={"Authorization": f"Bearer {raw_device_key}"},
        data={
            "event_type": "person_detected",
            "confidence_score": "0.91",
            "detected_at": "2026-08-14T12:00:00Z",
            "detected_objects": '["person"]',
        },
        files={"image": ("frame.jpg", b"jpeg-data", "image/jpeg")},
    )
    assert created.status_code == 201
    assert created.json()["analysis_task_id"] == "analysis-1"

    listing = client.get("/api/v1/events", headers={"Authorization": f"Bearer {token}"})
    assert listing.status_code == 200
    assert listing.json()[0]["device_name"] == "Front Door"
    assert client.get("/api/v1/events").status_code == 401


def test_device_keys_are_hashed_and_llm_uses_responses_api(api):
    assert "api_key" not in Device.__table__.columns
    assert "api_key_hash" in Device.__table__.columns
    event = SecurityEvent(
        event_type="motion",
        confidence_score=0.8,
        detected_objects="[]",
        face_analysis="{}",
        detected_at=datetime.now(timezone.utc),
    )
    event.device = Device(device_id="garage", name="Garage", api_key_hash="not-used")
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                output_text='{"alert_needed": false, "alert_level": "low", "reasoning": "routine", "recommended_action": "none", "summary": "motion"}'
            )

    result = request_analysis(SimpleNamespace(responses=FakeResponses()), event)
    assert result["alert_needed"] is False
    assert captured["model"]
    assert captured["text"]["format"]["type"] == "json_object"
