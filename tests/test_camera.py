from pathlib import Path

from app import create_app
from openscope.camera import MockCamera


def test_mock_camera_lifecycle_and_capture(tmp_path: Path):
    camera = MockCamera()
    app = create_app(camera=camera)
    app.config["CAMERA_CAPTURE_DIR"] = tmp_path
    client = app.test_client()

    assert client.get("/api/camera").get_json()["open"] is False
    assert client.post("/api/camera/open").status_code == 200
    response = client.post("/api/camera/capture", json={"filename": "test.jpg", "metadata": {"target": "M31"}})
    assert response.status_code == 200
    assert (tmp_path / "test.jpg").read_bytes()[:2] == b"\xff\xd8"
    assert (tmp_path / "test.jpg.json").exists()

    stream = client.get("/api/camera/stream")
    assert stream.status_code == 200
    assert stream.mimetype == "multipart/x-mixed-replace"

    assert client.post("/api/camera/close").get_json()["camera"]["open"] is False


def test_camera_rejects_capture_when_closed_and_bad_filename(tmp_path: Path):
    app = create_app(camera=MockCamera())
    app.config["CAMERA_CAPTURE_DIR"] = tmp_path
    client = app.test_client()
    assert client.post("/api/camera/capture", json={}).status_code == 400
    client.post("/api/camera/open")
    response = client.post("/api/camera/capture", json={"filename": "capture.png"})
    assert response.status_code == 400


def test_camera_stream_rejects_closed_camera():
    client = create_app(camera=MockCamera()).test_client()
    response = client.get("/api/camera/stream")
    assert response.status_code == 400
