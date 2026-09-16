import app as app_module
from app import create_app


def test_control_panel_and_status_endpoint():
    client = create_app().test_client()
    assert client.get("/").status_code == 200
    response = client.get("/api/status")
    assert response.status_code == 200
    assert len(response.get_json()["motors"]) == 5


def test_catalog_endpoint_returns_searchable_objects():
    client = create_app().test_client()
    response = client.get("/api/catalog/objects?q=M31")
    assert response.status_code == 200
    objects = response.get_json()["objects"]
    assert len(objects) == 1
    assert objects[0]["name"] == "Andromeda Galaxy"


def test_mount_alignment_endpoint_stores_current_position():
    client = create_app().test_client()
    response = client.post(
        "/api/mount/align",
        json={"ra_deg": 10.6847, "dec_deg": 41.2687, "source": "M31"},
    )
    assert response.status_code == 200
    assert response.get_json()["alignment"]["aligned"] is True
    assert client.get("/api/mount/position").get_json()["source"] == "M31"


def test_goto_plan_uses_alignment_without_moving_motors():
    client = create_app().test_client()
    client.post("/api/mount/align", json={"ra_deg": 350, "dec_deg": 20, "source": "manual"})
    response = client.post("/api/goto/plan", json={"name": "Target", "ra_deg": 10, "dec_deg": 5})
    assert response.status_code == 200
    plan = response.get_json()["plan"]
    assert plan["ra_delta_deg"] == 20
    assert plan["dec_delta_deg"] == -15
    assert plan["execution_supported"] is False
    assert client.get("/api/status").get_json()["motors"]["RA"]["state"] == "IDLE"


def test_telescope_calibration_records_references_and_estimates_scale():
    client = create_app().test_client()
    client.post("/api/calibration/mode", json={"enabled": True})
    client.post("/api/calibration/reference", json={"name": "A", "ra_deg": 10, "dec_deg": 5})
    client.post("/api/calibration/motion", json={"axis": "RA", "direction": "POS", "duration_ms": 1000})
    client.post("/api/calibration/motion", json={"axis": "DEC", "direction": "POS", "duration_ms": 1000})
    response = client.post("/api/calibration/reference", json={"name": "B", "ra_deg": 11, "dec_deg": 5.5})
    assert response.status_code == 200
    calibration = response.get_json()["calibration"]
    assert calibration["scale_deg_per_second"] == {"RA": 1.0, "DEC": 0.5}


def test_goto_plan_requires_alignment():
    response = create_app().test_client().post(
        "/api/goto/plan", json={"name": "Target", "ra_deg": 10, "dec_deg": 5}
    )
    assert response.status_code == 400


def test_visual_tracker_saves_up_to_three_manual_references():
    client = create_app().test_client()
    assert client.post("/api/visual-tracker/reference", json={"name": "Moon", "ra_deg": 10, "dec_deg": 5}).status_code == 400
    assert client.post("/api/visual-tracker/mode", json={"enabled": True}).status_code == 200
    for index in range(4):
        response = client.post(
            "/api/visual-tracker/reference",
            json={"name": f"Object {index}", "ra_deg": index + 1, "dec_deg": index},
        )
        assert response.status_code == 200
    status = client.get("/api/visual-tracker").get_json()
    assert len(status["references"]) == 3
    assert status["references"][-1]["name"] == "Object 3"


def test_visual_tracker_reference_reset_clears_alignment_and_target():
    client = create_app().test_client()
    client.post("/api/visual-tracker/mode", json={"enabled": True})
    client.post("/api/visual-tracker/reference", json={"name": "Moon", "ra_deg": 10, "dec_deg": 5})
    response = client.post("/api/visual-tracker/references/reset")
    assert response.status_code == 200
    assert response.get_json()["visual_tracker"]["references"] == []
    assert response.get_json()["alignment"]["aligned"] is False


def test_visual_tracker_prepares_next_target_without_moving_motors():
    client = create_app().test_client()
    client.post("/api/visual-tracker/mode", json={"enabled": True})
    client.post("/api/visual-tracker/reference", json={"name": "Moon", "ra_deg": 350, "dec_deg": 20})
    response = client.post("/api/visual-tracker/target", json={"name": "M31", "ra_deg": 10, "dec_deg": 5})
    assert response.status_code == 200
    assert response.get_json()["target"]["ra_delta_deg"] == 20
    assert response.get_json()["target"]["execution_supported"] is False
    assert client.get("/api/status").get_json()["motors"]["RA"]["state"] == "IDLE"


def test_catalog_endpoint_rejects_visible_query_without_observer_data():
    client = create_app().test_client()
    response = client.get("/api/catalog/objects?visible=true")
    assert response.status_code == 400


def test_catalog_endpoint_returns_dynamic_solar_system_objects():
    import pytest

    pytest.importorskip("astropy")
    client = create_app().test_client()
    response = client.get(
        "/api/catalog/objects?latitude_deg=0&longitude_deg=0&observation_time=2025-01-01T00:00:00Z"
    )
    assert response.status_code == 200
    ids = {item["id"] for item in response.get_json()["objects"]}
    assert {"MERCURY", "VENUS", "MARS", "JUPITER", "SATURN", "URANUS", "NEPTUNE"}.issubset(ids)


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
