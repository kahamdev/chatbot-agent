from fastapi.testclient import TestClient

from chatbot_agent.main import create_app
from tests.conftest import make_settings


def test_health_and_ready_do_not_require_auth() -> None:
    with TestClient(create_app(make_settings())) as client:
        health = client.get("/health")
        ready = client.get("/ready")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 200
    assert ready.json() == {"status": "ready"}
    assert health.headers["x-content-type-options"] == "nosniff"
