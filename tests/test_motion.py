from openscope.core.motor import MOTOR_IDS, MotorDirection, MotorState
from openscope.core.telescope import TelescopeState
from openscope.devices.mock import MockDevice
from openscope.motion.controller import MotionController


def test_default_state_represents_five_channels():
    state = TelescopeState.with_default_channels({"RA": True, "DEC": True})
    assert tuple(state.motors) == MOTOR_IDS
    assert state.motor("RA").enabled is True
    assert state.motor("FOCUS").enabled is False


def test_mock_device_move_stop_status_and_emergency_stop():
    state = TelescopeState.with_default_channels({"RA": True, "DEC": True})
    device = MockDevice(state)
    device.move("RA", MotorDirection.POS, speed=1.0)
    assert device.status()["motors"]["RA"]["state"] == MotorState.MOVING
    device.stop("RA")
    device.move("DEC", MotorDirection.NEG, speed=1.0)
    device.emergency_stop()
    assert state.motor("RA").state is MotorState.IDLE
    assert state.motor("DEC").state is MotorState.IDLE
    assert state.motor("FOCUS").state is MotorState.DISABLED
    assert device.command_log[-1] == ("STOP", "ALL", None)


def test_motion_controller_updates_open_loop_ra_dec_rates_without_feedback():
    state = TelescopeState.with_default_channels({"RA": True, "DEC": True})
    device = MockDevice(state)
    controller = MotionController(device, state)

    controller.set_rate_pair(0.004178, -0.002)
    assert state.motor("RA").state is MotorState.MOVING
    assert state.motor("DEC").state is MotorState.MOVING
    assert device.command_log[-2:] == [
        ("MOVE", "RA", "POS"),
        ("MOVE", "DEC", "NEG"),
    ]

    controller.set_rate_pair(0.0, 0.0)
    assert state.motor("RA").state is MotorState.IDLE
    assert state.motor("DEC").state is MotorState.IDLE


def test_mount_alignment_stores_open_loop_coordinates_without_feedback():
    state = TelescopeState.with_default_channels({"RA": True, "DEC": True})
    state.alignment.set_position(10.6847, 41.2687, "M31")

    assert state.alignment.aligned is True
    assert state.alignment.ra_deg == 10.6847
    assert state.alignment.dec_deg == 41.2687
    assert state.alignment.as_dict()["feedback_required"] is False
