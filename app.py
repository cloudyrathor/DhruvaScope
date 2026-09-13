from pathlib import Path

from flask import Flask, jsonify, render_template, request

from openscope.configuration import load_yaml, telescope_state_from_config
from openscope.core.errors import ConfigurationError
from openscope.core.errors import DeviceError
from openscope.core.motor import MotorDirection
from openscope.devices.mock import MockDevice
from openscope.devices.remote import Esp32Device
from openscope.transport.bluetooth import BluetoothTransport
from openscope.transport.wifi import WifiTransport
from openscope.tracking.astronomy import AstronomyService, EquatorialTarget, ObserverLocation
from openscope.tracking.tracker import SiderealTracker
from openscope.motion.controller import MotionController

DEFAULT_WIFI_HOST = "192.168.4.1"
DEFAULT_WIFI_PORT = 9999


def create_app(config_path: str | Path | None = None, device=None) -> Flask:
    """Create the DhruvaScope web application with an injectable device."""
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    path = Path(config_path or Path(__file__).parent / "config" / "example_equatorial.yaml")
    state = telescope_state_from_config(load_yaml(path))
    app.config["TELESCOPE_DEVICE"] = device or MockDevice(state)
    app.config["ASTRONOMY_SERVICE"] = AstronomyService()
    app.config["MOTION_CONTROLLER"] = MotionController(app.config["TELESCOPE_DEVICE"], state)
    app.config["SIDEREAL_TRACKER"] = SiderealTracker(
        app.config["TELESCOPE_DEVICE"], motion=app.config["MOTION_CONTROLLER"]
    )

    @app.get("/")
    def index():
        return render_template("control_panel.html")

    @app.get("/api/status")
    def status():
        return jsonify(app.config["TELESCOPE_DEVICE"].status())

    @app.get("/api/motors")
    def motors():
        return jsonify(app.config["TELESCOPE_DEVICE"].status()["motors"])

    @app.get("/api/connection")
    def connection():
        device = app.config["TELESCOPE_DEVICE"]
        return jsonify({"mode": app.config.get("CONNECTION_MODE", "mock"), "device": type(device).__name__})

    @app.post("/api/connect")
    def connect():
        data = request.get_json(silent=True) or {}
        mode = data.get("mode", "mock").lower()
        try:
            if mode == "mock":
                device = MockDevice(state)
            elif mode == "wifi":
                host = str(data.get("host", DEFAULT_WIFI_HOST)).strip()
                if not host:
                    raise ConfigurationError("Wi-Fi address is required (usually 192.168.4.1 in AP mode)")
                device = Esp32Device(WifiTransport(host, int(data.get("port", DEFAULT_WIFI_PORT))), state)
            elif mode == "bluetooth":
                device = Esp32Device(BluetoothTransport(str(data["port"]), int(data.get("baudrate", 115200))), state)
            else:
                raise ConfigurationError("mode must be mock, wifi, or bluetooth")
            initial_status = device.status()
            old_device = app.config["TELESCOPE_DEVICE"]
            if hasattr(old_device, "close"):
                old_device.close()
            app.config["TELESCOPE_DEVICE"] = device
            app.config["MOTION_CONTROLLER"] = MotionController(device, state)
            app.config["SIDEREAL_TRACKER"] = SiderealTracker(device, motion=app.config["MOTION_CONTROLLER"])
            app.config["CONNECTION_MODE"] = mode
            return jsonify({"ok": True, "mode": mode, "status": initial_status})
        except (ConfigurationError, DeviceError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/disconnect")
    def disconnect():
        device = app.config["TELESCOPE_DEVICE"]
        if hasattr(device, "close"):
            device.close()
        app.config["TELESCOPE_DEVICE"] = MockDevice(state)
        app.config["MOTION_CONTROLLER"] = MotionController(app.config["TELESCOPE_DEVICE"], state)
        app.config["SIDEREAL_TRACKER"] = SiderealTracker(
            app.config["TELESCOPE_DEVICE"], motion=app.config["MOTION_CONTROLLER"]
        )
        app.config["CONNECTION_MODE"] = "mock"
        return jsonify({"ok": True, "mode": "mock"})

    @app.get("/api/tracking")
    def tracking_status():
        return jsonify(app.config["SIDEREAL_TRACKER"].status())

    @app.post("/api/tracking/sidereal/start")
    def start_sidereal_tracking():
        try:
            tracker = app.config["SIDEREAL_TRACKER"]
            tracker.start()
            return jsonify({"ok": True, "tracking": tracker.status()})
        except (ConfigurationError, DeviceError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/tracking/stop")
    def stop_tracking():
        try:
            tracker = app.config["SIDEREAL_TRACKER"]
            tracker.stop()
            return jsonify({"ok": True, "tracking": tracker.status()})
        except (ConfigurationError, DeviceError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/astronomy/target")
    def calculate_target():
        data = request.get_json(silent=True) or {}
        try:
            target = EquatorialTarget(
                name=str(data["name"]),
                ra_deg=float(data["ra_deg"]),
                dec_deg=float(data["dec_deg"]),
            )
            observer = ObserverLocation(
                latitude_deg=float(data["latitude_deg"]),
                longitude_deg=float(data["longitude_deg"]),
                elevation_m=float(data.get("elevation_m", 0.0)),
            )
            solution = app.config["ASTRONOMY_SERVICE"].calculate_target(
                target,
                observer,
                data["observation_time"],
                mount_type=state.mount_type,
            )
            return jsonify({"ok": True, "target": solution.as_dict()})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/tracking/rates")
    def set_tracking_rates():
        data = request.get_json(silent=True) or {}
        try:
            app.config["MOTION_CONTROLLER"].set_rate_pair(
                float(data.get("ra_rate", 0.0)),
                float(data.get("dec_rate", 0.0)),
            )
            return jsonify({"ok": True, "status": app.config["TELESCOPE_DEVICE"].status()})
        except (ConfigurationError, DeviceError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/motor/<motor_id>/move")
    def move(motor_id: str):
        data = request.get_json(silent=True) or {}
        try:
            direction = MotorDirection(data.get("direction", ""))
            speed = data.get("speed")
            if speed is not None:
                speed = float(speed)
            app.config["TELESCOPE_DEVICE"].move(motor_id, direction, speed)
            return jsonify({"ok": True, "status": app.config["TELESCOPE_DEVICE"].status()})
        except (ConfigurationError, DeviceError, ValueError, TypeError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/motor/<motor_id>/stop")
    def stop(motor_id: str):
        try:
            app.config["TELESCOPE_DEVICE"].stop(motor_id)
            return jsonify({"ok": True})
        except (ConfigurationError, DeviceError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/motor/<motor_id>/speed")
    def speed(motor_id: str):
        data = request.get_json(silent=True) or {}
        try:
            app.config["TELESCOPE_DEVICE"].set_speed(motor_id, float(data["speed"]))
            return jsonify({"ok": True})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/stop")
    def emergency_stop():
        app.config["TELESCOPE_DEVICE"].emergency_stop()
        app.config["SIDEREAL_TRACKER"]._running = False
        return jsonify({"ok": True})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
