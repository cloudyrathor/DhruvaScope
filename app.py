from pathlib import Path
from datetime import datetime, timezone

from flask import Flask, Response, jsonify, render_template, request

from openscope.configuration import load_yaml, telescope_state_from_config
from openscope.catalog import list_catalog_objects, list_solar_system_objects, list_visible_catalog_objects
from openscope.core.errors import ConfigurationError
from openscope.core.errors import DeviceError
from openscope.core.motor import MotorDirection
from openscope.devices.mock import MockDevice
from openscope.devices.remote import Esp32Device
from openscope.transport.bluetooth import BluetoothTransport
from openscope.transport.wifi import WifiTransport
from openscope.tracking.astronomy import AstronomyService, EquatorialTarget, ObserverLocation
from openscope.tracking.moon import MoonService
from openscope.tracking.tracker import SiderealTracker
from openscope.motion.controller import MotionController
from openscope.motion.goto import GoToPlanner
from openscope.camera import Camera, MockCamera, OpenCVCamera

DEFAULT_WIFI_HOST = "192.168.4.1"
DEFAULT_WIFI_PORT = 9999


def create_app(config_path: str | Path | None = None, device=None, camera: Camera | None = None) -> Flask:
    """Create the DhruvaScope web application with an injectable device."""
    app = Flask(__name__, template_folder="web/templates", static_folder="web/static")
    path = Path(config_path or Path(__file__).parent / "config" / "example_equatorial.yaml")
    state = telescope_state_from_config(load_yaml(path))
    app.config["TELESCOPE_DEVICE"] = device or MockDevice(state)
    app.config["CAMERA"] = camera or MockCamera()
    app.config["CAMERA_CAPTURE_DIR"] = Path(app.root_path) / "captures"
    app.config["VISUAL_TRACKER"] = {
        "enabled": False,
        "references": [],
        "target": None,
    }
    app.config["TELESCOPE_CALIBRATION"] = {
        "enabled": False,
        "points": [],
        "travel_ms": {"RA": 0.0, "DEC": 0.0},
        "scale_deg_per_second": {"RA": None, "DEC": None},
    }
    app.config["ASTRONOMY_SERVICE"] = AstronomyService()
    app.config["MOON_SERVICE"] = MoonService()
    app.config["MOTION_CONTROLLER"] = MotionController(app.config["TELESCOPE_DEVICE"], state)
    app.config["GOTO_PLANNER"] = GoToPlanner()
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

    @app.get("/api/mount/position")
    def mount_position():
        return jsonify(state.alignment.as_dict())

    @app.get("/api/visual-tracker")
    def visual_tracker_status():
        return jsonify(app.config["VISUAL_TRACKER"])

    @app.post("/api/visual-tracker/mode")
    def visual_tracker_mode():
        data = request.get_json(silent=True) or {}
        enabled = bool(data.get("enabled", False))
        app.config["VISUAL_TRACKER"]["enabled"] = enabled
        if not enabled:
            app.config["TELESCOPE_DEVICE"].stop("RA")
            app.config["TELESCOPE_DEVICE"].stop("DEC")
        return jsonify({"ok": True, "visual_tracker": app.config["VISUAL_TRACKER"]})

    @app.post("/api/visual-tracker/reference")
    def save_visual_reference():
        data = request.get_json(silent=True) or {}
        try:
            if not app.config["VISUAL_TRACKER"]["enabled"]:
                raise ConfigurationError("enable visual tracker mode first")
            name = str(data["name"]).strip()
            ra_deg = float(data["ra_deg"])
            dec_deg = float(data["dec_deg"])
            if not name:
                raise ConfigurationError("reference object name is required")
            # A confirmed visual reference is also the current open-loop mount
            # alignment used by the existing GoTo planner.
            state.alignment.set_position(ra_deg, dec_deg, name)
            references = app.config["VISUAL_TRACKER"]["references"]
            references.append({"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg})
            del references[:-3]
            app.config["VISUAL_TRACKER"]["target"] = name
            return jsonify({"ok": True, "reference": references[-1], "visual_tracker": app.config["VISUAL_TRACKER"]})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/visual-tracker/references/reset")
    def reset_visual_references():
        tracker = app.config["VISUAL_TRACKER"]
        tracker["references"] = []
        tracker["target"] = None
        state.alignment.clear()
        return jsonify({"ok": True, "visual_tracker": tracker, "alignment": state.alignment.as_dict()})

    @app.post("/api/visual-tracker/target")
    def prepare_visual_target():
        data = request.get_json(silent=True) or {}
        try:
            if not app.config["VISUAL_TRACKER"]["enabled"]:
                raise ConfigurationError("enable visual tracker mode first")
            plan = app.config["GOTO_PLANNER"].plan(
                state.alignment,
                float(data["ra_deg"]),
                float(data["dec_deg"]),
                str(data["name"]),
            )
            app.config["VISUAL_TRACKER"]["target"] = plan.as_dict()
            return jsonify({"ok": True, "target": app.config["VISUAL_TRACKER"]["target"]})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/calibration")
    def calibration_status():
        return jsonify(app.config["TELESCOPE_CALIBRATION"])

    @app.post("/api/calibration/mode")
    def calibration_mode():
        data = request.get_json(silent=True) or {}
        calibration = app.config["TELESCOPE_CALIBRATION"]
        calibration["enabled"] = bool(data.get("enabled", False))
        return jsonify({"ok": True, "calibration": calibration})

    @app.post("/api/calibration/reset")
    def calibration_reset():
        calibration = app.config["TELESCOPE_CALIBRATION"]
        calibration["points"] = []
        calibration["travel_ms"] = {"RA": 0.0, "DEC": 0.0}
        calibration["scale_deg_per_second"] = {"RA": None, "DEC": None}
        return jsonify({"ok": True, "calibration": calibration})

    @app.post("/api/calibration/motion")
    def calibration_motion():
        data = request.get_json(silent=True) or {}
        try:
            calibration = app.config["TELESCOPE_CALIBRATION"]
            if not calibration["enabled"]:
                raise ConfigurationError("enable telescope calibration mode first")
            axis = str(data["axis"]).upper()
            direction = str(data["direction"]).upper()
            duration_ms = float(data["duration_ms"])
            if axis not in {"RA", "DEC"} or direction not in {"POS", "NEG"} or not 0 <= duration_ms <= 300000:
                raise ConfigurationError("invalid calibration movement")
            calibration["travel_ms"][axis] += duration_ms if direction == "POS" else -duration_ms
            return jsonify({"ok": True, "calibration": calibration})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/calibration/reference")
    def calibration_reference():
        data = request.get_json(silent=True) or {}
        try:
            calibration = app.config["TELESCOPE_CALIBRATION"]
            if not calibration["enabled"]:
                raise ConfigurationError("enable telescope calibration mode first")
            name = str(data["name"]).strip()
            ra_deg = float(data["ra_deg"])
            dec_deg = float(data["dec_deg"])
            state.alignment.set_position(ra_deg, dec_deg, name)
            calibration["points"].append({"name": name, "ra_deg": ra_deg, "dec_deg": dec_deg, "travel_ms": dict(calibration["travel_ms"])})
            del calibration["points"][:-6]
            if len(calibration["points"]) >= 2:
                first = calibration["points"][0]
                last = calibration["points"][-1]
                for axis, coordinate in (("RA", "ra_deg"), ("DEC", "dec_deg")):
                    elapsed = last["travel_ms"][axis] - first["travel_ms"][axis]
                    if elapsed:
                        delta = last[coordinate] - first[coordinate]
                        if axis == "RA":
                            delta = (delta + 180) % 360 - 180
                        calibration["scale_deg_per_second"][axis] = delta / (elapsed / 1000)
            return jsonify({"ok": True, "calibration": calibration})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/mount/align")
    def align_mount():
        data = request.get_json(silent=True) or {}
        try:
            state.alignment.set_position(
                float(data["ra_deg"]),
                float(data["dec_deg"]),
                str(data.get("source", "manual")),
            )
            return jsonify({"ok": True, "alignment": state.alignment.as_dict()})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/goto/plan")
    def plan_goto():
        data = request.get_json(silent=True) or {}
        try:
            plan = app.config["GOTO_PLANNER"].plan(
                state.alignment,
                float(data["ra_deg"]),
                float(data["dec_deg"]),
                str(data.get("name", "target")),
            )
            return jsonify({"ok": True, "plan": plan.as_dict()})
        except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/connection")
    def connection():
        device = app.config["TELESCOPE_DEVICE"]
        return jsonify({"mode": app.config.get("CONNECTION_MODE", "mock"), "device": type(device).__name__})

    @app.get("/api/camera")
    def camera_status():
        return jsonify(app.config["CAMERA"].status)

    @app.post("/api/camera/open")
    def camera_open():
        data = request.get_json(silent=True) or {}
        try:
            current = app.config["CAMERA"]
            if data.get("type", "mock") == "opencv":
                current.close()
                source = data.get("source", 0)
                source = int(source) if str(source).isdigit() else str(source)
                current = OpenCVCamera(source)
                app.config["CAMERA"] = current
            elif data.get("type", "mock") != "mock":
                raise ConfigurationError("camera type must be mock or opencv")
            current.open()
            return jsonify({"ok": True, "camera": current.status})
        except (ConfigurationError, DeviceError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/api/camera/close")
    def camera_close():
        app.config["CAMERA"].close()
        return jsonify({"ok": True, "camera": app.config["CAMERA"].status})

    @app.post("/api/camera/capture")
    def camera_capture():
        data = request.get_json(silent=True) or {}
        try:
            filename = Path(str(data.get("filename", "capture.jpg"))).name
            if Path(filename).suffix.lower() not in {".jpg", ".jpeg"}:
                raise ConfigurationError("filename must end in .jpg or .jpeg")
            record = app.config["CAMERA"].capture(
                app.config["CAMERA_CAPTURE_DIR"] / filename,
                {"captured_by": "DhruvaScope", "requested_at": datetime.now(timezone.utc).isoformat(), **data.get("metadata", {})},
            )
            return jsonify({"ok": True, "capture": record})
        except (ConfigurationError, DeviceError, TypeError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.get("/api/camera/stream")
    def camera_stream():
        def frames():
            camera = app.config["CAMERA"]
            while camera.status["open"]:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + camera.read() + b"\r\n"

        if not app.config["CAMERA"].status["open"]:
            return jsonify({"ok": False, "error": "camera is not open"}), 400
        return Response(frames(), mimetype="multipart/x-mixed-replace; boundary=frame")

    @app.get("/api/catalog/objects")
    def catalog_objects():
        query = request.args.get("q", "")
        if request.args.get("visible", "false").lower() == "true" and "observation_time" not in request.args:
            return jsonify({"ok": False, "error": "observer location and observation_time are required for visible objects"}), 400
        if "observation_time" in request.args:
            try:
                observer = ObserverLocation(
                    latitude_deg=float(request.args["latitude_deg"]),
                    longitude_deg=float(request.args["longitude_deg"]),
                    elevation_m=float(request.args.get("elevation_m", 0.0)),
                )
                observation_time = request.args["observation_time"]
                visible_only = request.args.get("visible", "false").lower() == "true"
                fixed_objects = (
                    list_visible_catalog_objects(observer, observation_time)
                    if visible_only
                    else list_catalog_objects()
                )
                solar_objects = list_solar_system_objects(observer, observation_time)
                objects = fixed_objects + (
                    [obj for obj in solar_objects if obj["above_horizon"]]
                    if visible_only
                    else solar_objects
                )
                if query:
                    needle = query.casefold()
                    objects = [
                        obj for obj in objects
                        if needle in str(obj["id"]).casefold()
                        or needle in str(obj["name"]).casefold()
                        or needle in str(obj["object_type"]).casefold()
                    ]
                objects.sort(key=lambda obj: float(obj.get("altitude_deg", -999.0)), reverse=True)
                return jsonify({"objects": objects, "visible_only": visible_only})
            except (ConfigurationError, KeyError, TypeError, ValueError) as exc:
                return jsonify({"ok": False, "error": str(exc)}), 400
        return jsonify({"objects": list_catalog_objects(query), "visible_only": False})

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

    @app.post("/api/astronomy/moon")
    def calculate_moon():
        data = request.get_json(silent=True) or {}
        try:
            observer = ObserverLocation(
                latitude_deg=float(data["latitude_deg"]),
                longitude_deg=float(data["longitude_deg"]),
                elevation_m=float(data.get("elevation_m", 0.0)),
            )
            solution = app.config["MOON_SERVICE"].calculate(
                observer,
                data["observation_time"],
                mount_type=state.mount_type,
            )
            return jsonify({"ok": True, "moon": solution.as_dict()})
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
