from types import SimpleNamespace

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor.tmc5160 import MotorDriverTMC5160


class DummyAppState:
    def __init__(self, *, use_dummy_driver: bool = True):
        self.mechanical_setup = MechanicalSetup(mm_per_revolution=4.0)
        self.config = SimpleNamespace(
            USE_DUMMY_DRIVER=use_dummy_driver,
            DEFAULT_GLOBAL_SCALER=0,
            DEFAULT_RSENSE=75,
        )


def _make_driver(**kwargs) -> MotorDriverTMC5160:
    return MotorDriverTMC5160(
        DummyAppState(use_dummy_driver=True),
        step_mode=16,
        **kwargs,
    )


def test_tmc5160_requires_pytrinamic_when_not_dummy():
    with pytest.raises((NotImplementedError, ModuleNotFoundError, ConnectionError)):
        MotorDriverTMC5160(DummyAppState(use_dummy_driver=False))


def test_tmc5160_dummy_driver_supports_basic_motion():
    driver = _make_driver()

    driver.enable_motor()
    driver.move_up(8.0, 2.0)
    assert driver.get_current_position_mm() == pytest.approx(8.0)

    driver.run_to_position(3.0)
    assert driver.get_current_position_mm() == pytest.approx(3.0)


def test_tmc5160_enable_disable():
    driver = _make_driver()
    driver.enable_motor()
    assert driver.is_motor_enabled() == 1
    driver.disable_motor()
    assert driver.is_motor_enabled() == 0


def test_tmc5160_ramp_parameters_roundtrip():
    driver = _make_driver()
    driver.set_ramp_parameters(
        a1=1000, v1=50000, amax=500, vmax=200000,
        dmax=700, d1=1400, vstart=0, vstop=10,
    )
    assert driver.get_a1() == 1000
    assert driver.get_v1() == 50000
    assert driver.get_amax() == 500
    assert driver.get_vmax() == 200000
    assert driver.get_dmax() == 700
    assert driver.get_d1() == 1400
    assert driver.get_vstart() == 0
    assert driver.get_vstop() == 10


def test_tmc5160_individual_ramp_setters():
    driver = _make_driver()
    driver.set_a1(2000)
    assert driver.get_a1() == 2000
    driver.set_v1(100000)
    assert driver.get_v1() == 100000
    driver.set_d1(800)
    assert driver.get_d1() == 800
    driver.set_dmax(900)
    assert driver.get_dmax() == 900
    driver.set_vstart(5)
    assert driver.get_vstart() == 5
    driver.set_vstop(20)
    assert driver.get_vstop() == 20
    driver.set_tzerowait(100)
    assert driver.get_tzerowait() == 100


def test_tmc5160_vstop_minimum():
    driver = _make_driver()
    driver.set_vstop(0)
    assert driver.get_vstop() >= 1


def test_tmc5160_global_scaler_roundtrip():
    driver = _make_driver()
    driver.set_global_scaler(128)
    assert driver.get_global_scaler() == 128

    driver.set_global_scaler(0)
    assert driver.get_global_scaler() == 0

    with pytest.raises(ValueError):
        driver.set_global_scaler(10)  # 1-31 is invalid


def test_tmc5160_current_conversion():
    driver = _make_driver(global_scaler=0, rsense_mOhm=75)
    # With GLOBAL_SCALER=0 (256), rsense=75mOhm, V_FS=325mV:
    # At CS=31: I_rms ≈ 3065 mA
    cs = driver._convert_current_to_cs(3000)
    assert 28 <= cs <= 31
    actual = driver._convert_cs_to_current(cs)
    assert abs(actual - 3000) < 200  # within 200mA


def test_tmc5160_microsteps():
    driver = _make_driver()
    assert driver.get_microsteps() == 16
    driver.set_microsteps(32)
    assert driver.get_microsteps() == 32


def test_tmc5160_move_down():
    driver = _make_driver()
    driver.enable_motor()
    driver.move_up(10.0, 2.0)
    driver.move_down(4.0, 2.0)
    assert driver.get_current_position_mm() == pytest.approx(6.0)


def test_tmc5160_direction_inversion():
    driver = _make_driver()
    driver.enable_motor()
    driver.invert_direction(True)
    driver.move_up(5.0, 2.0)
    # With inverted direction, move_up should go negative
    assert driver.get_current_position_mm() == pytest.approx(-5.0)


def test_tmc5160_register_access():
    driver = _make_driver()
    driver._write_register(0x99, 42)
    assert driver._read_register(0x99) == 42


def test_tmc5160_drv_status_and_ramp_stat():
    driver = _make_driver()
    # Should return 0 in dummy mode
    assert driver.read_drv_status() == 0
    assert driver.read_ramp_status() == 0


def test_tmc5160_cleanup():
    driver = _make_driver()
    driver.enable_motor()
    driver.cleanup()
    assert driver.is_motor_enabled() == 0
