from fastapi.testclient import TestClient
from backend.app.main import app


def test_cryptoquest_npc_requires_server_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = TestClient(app)
    response = client.post(
        "/api/v1/cryptoquest/npc/dialogue",
        json={
            "npc_id": "blacksmith_01",
            "npc_name": "Doran",
            "npc_role": "blacksmith",
            "player_id": "player_test",
            "player_name": "Tester",
            "message": "Any work for me?",
            "world_state": "Bastion",
        },
    )
    assert response.status_code == 503
    assert response.json()["detail"]["error_code"] == "npc_ai_not_configured"
