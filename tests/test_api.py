from app import create_app


def test_control_panel_and_status_endpoint():
    client = create_app().test_client()
    assert client.get("/").status_code == 200
    response = client.get("/api/status")
    assert response.status_code == 200
    assert len(response.get_json()["motors"]) == 5


def test_api_validates_commands_and_supports_stop():
    client = create_app().test_client()
    assert client.post("/api/motor/RA/move", json={"direction": "POS", "speed": 1}).status_code == 200
    assert client.post("/api/motor/RA/move", json={"direction": "BAD", "speed": 1}).status_code == 400
    assert client.post("/api/stop").status_code == 200
