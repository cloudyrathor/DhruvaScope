import pytest

from openscope.core.errors import ConfigurationError
from openscope.core.motor import MotorChannel, MotorDirection, MotorState


def test_motor_validates_speed_and_moves():
    motor = MotorChannel("RA", "Right Ascension", max_speed=2.0)
    motor.move(MotorDirection.POS, speed=1.0)
    assert motor.state is MotorState.MOVING
    assert motor.speed == 1.0
    motor.stop()
    assert motor.state is MotorState.IDLE


def test_motor_rejects_invalid_speed():
    motor = MotorChannel("RA", "Right Ascension", max_speed=2.0)
    with pytest.raises(ConfigurationError):
        motor.set_speed(3.0)


def test_disabled_motor_cannot_move():
    motor = MotorChannel("AUX1", "Auxiliary 1", enabled=False)
    with pytest.raises(ConfigurationError):
        motor.move(MotorDirection.POS, speed=1.0)
