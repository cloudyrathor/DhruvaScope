import app as app_module
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


def test_astronomy_target_endpoint_validates_coordinate_workflow():
    import pytest

    pytest.importorskip("astropy")
    client = create_app().test_client()
    response = client.post(
        "/api/astronomy/target",
        json={
            "name": "Test Star",
            "ra_deg": 0.0,
            "dec_deg": 0.0,
            "latitude_deg": 0.0,
            "longitude_deg": 0.0,
            "observation_time": "2025-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["target"]["name"] == "Test Star"


def test_moon_endpoint_returns_current_position():
    import pytest

    pytest.importorskip("astropy")
    client = create_app().test_client()
    response = client.post(
        "/api/astronomy/moon",
        json={
            "latitude_deg": 0.0,
            "longitude_deg": 0.0,
            "observation_time": "2025-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 200
    assert response.get_json()["moon"]["name"] == "Moon"


def test_wifi_connection_uses_default_ap_address(monkeypatch):
    seen = {}

    class FakeDevice:
        def __init__(self, transport, state):
            seen["host"] = transport.host
            seen["port"] = transport.port

        def status(self):
            return {"device": "fake", "motors": {}}

        def close(self):
            pass

    monkeypatch.setattr(app_module, "Esp32Device", FakeDevice)
    response = create_app().test_client().post("/api/connect", json={"mode": "wifi"})

    assert response.status_code == 200
    assert seen == {"host": "192.168.4.1", "port": 9999}


def test_wifi_connection_rejects_blank_address():
    response = create_app().test_client().post("/api/connect", json={"mode": "wifi", "host": "   "})

    assert response.status_code == 400
    assert "address is required" in response.get_json()["error"]
