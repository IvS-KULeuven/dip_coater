from types import SimpleNamespace

import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup
from dip_coater.motor_driver.tmc5160 import tmc5160 as tmc5160_module
from dip_coater.motor_driver.tmc5160 import MotorDriverTMC5160


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


def test_tmc5160_requires_pytrinamic_when_not_dummy(monkeypatch):
    monkeypatch.setattr(tmc5160_module, "_PYTRINAMIC_AVAILABLE", False)

    with pytest.raises(ModuleNotFoundError):
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

    driver.set_global_scaler(10)
    assert driver.get_global_scaler() == 10

    driver.set_global_scaler(0)
    assert driver.get_global_scaler() == 0

    with pytest.raises(ValueError):
        driver.set_global_scaler(256)


def test_tmc5160_current_conversion():
    driver = _make_driver(global_scaler=0, rsense_mOhm=75)
    # With GLOBAL_SCALER=0 (256), rsense=75mOhm, V_FS=325mV:
    # At CS=31: I_rms ≈ 3065 mA
    cs = driver._convert_current_to_cs(3000)
    assert cs in (30, 31)
    actual = driver._convert_cs_to_current(cs)
    assert abs(actual - 3000) < 100

    with pytest.raises(ValueError):
        driver._convert_current_to_cs(4000)


@pytest.mark.parametrize("current_mA, gs, rsense, expected_cs", [
    # GLOBAL_SCALER=0 (full scale=256), Rsense=50mOhm
    (500,  0, 50,  2),
    (1000, 0, 50,  6),
    (1500, 0, 50,  9),
    (2000, 0, 50, 13),
    (3000, 0, 50, 20),
    (4000, 0, 50, 27),
    # GLOBAL_SCALER=0 (full scale=256), Rsense=75mOhm
    (500,  0, 75,  4),
    (1000, 0, 75,  9),
    (1500, 0, 75, 15),
    (2000, 0, 75, 20),
    (3000, 0, 75, 30),
    # GLOBAL_SCALER=128 (half scale), Rsense=50mOhm
    (500,  128, 50,  6),
    (1000, 128, 50, 13),
    (1500, 128, 50, 20),
    (2000, 128, 50, 27),
])
def test_tmc5160_current_to_cs_hardcoded(current_mA, gs, rsense, expected_cs):
    driver = _make_driver(global_scaler=gs, rsense_mOhm=rsense)
    assert driver._convert_current_to_cs(current_mA) == expected_cs


@pytest.mark.parametrize("cs, gs, rsense, expected_mA", [
    # GLOBAL_SCALER=0 (full scale=256), Rsense=50mOhm
    (0,  0, 50,  143.6),
    (6,  0, 50, 1005.4),
    (13, 0, 50, 2010.8),
    (31, 0, 50, 4596.2),
    # GLOBAL_SCALER=0 (full scale=256), Rsense=75mOhm
    (0,  0, 75,   95.8),
    (9,  0, 75,  957.5),
    (31, 0, 75, 3064.1),
    # GLOBAL_SCALER=128, Rsense=50mOhm — half the full-scale values
    (0,  128, 50,   71.8),
    (13, 128, 50, 1005.4),
    (31, 128, 50, 2298.1),
])
def test_tmc5160_cs_to_current_hardcoded(cs, gs, rsense, expected_mA):
    driver = _make_driver(global_scaler=gs, rsense_mOhm=rsense)
    assert driver._convert_cs_to_current(cs) == pytest.approx(expected_mA, abs=0.1)


def test_tmc5160_current_conversion_roundtrip():
    """CS -> mA -> CS should be identity for all valid CS values."""
    driver = _make_driver(global_scaler=0, rsense_mOhm=75)
    for cs in range(0, 32):
        current = driver._convert_cs_to_current(cs)
        assert driver._convert_current_to_cs(current) == cs


def test_tmc5160_current_conversion_zero():
    """0 mA maps to CS=0; CS=0 is 1/32 of full scale, not 0 mA."""
    driver = _make_driver(global_scaler=0, rsense_mOhm=50)
    assert driver._convert_current_to_cs(0) == 0
    # CS=0 means (0+1)/32 of full scale, so it's a small but non-zero current
    assert driver._convert_cs_to_current(0) > 0


def test_tmc5160_current_conversion_negative_raises():
    driver = _make_driver(global_scaler=0, rsense_mOhm=50)
    with pytest.raises(ValueError):
        driver._convert_current_to_cs(-100)


def test_tmc5160_current_conversion_with_global_scaler():
    """Lower GLOBAL_SCALER reduces the max achievable current."""
    driver_full = _make_driver(global_scaler=0, rsense_mOhm=50)
    driver_half = _make_driver(global_scaler=128, rsense_mOhm=50)

    max_full = driver_full._convert_cs_to_current(31)
    max_half = driver_half._convert_cs_to_current(31)
    assert max_half == pytest.approx(max_full / 2, rel=0.01)

    # Same target current requires higher CS with lower scaler
    target = 1000
    cs_full = driver_full._convert_current_to_cs(target)
    cs_half = driver_half._convert_current_to_cs(target)
    assert cs_half > cs_full


def test_tmc5160_current_conversion_scaler_changes():
    """Changing global scaler on the same driver affects conversion."""
    driver = _make_driver(global_scaler=0, rsense_mOhm=50)
    cs_full = driver._convert_current_to_cs(1500)

    driver.set_global_scaler(128)
    cs_half = driver._convert_current_to_cs(1500)
    assert cs_half > cs_full


def test_tmc5160_current_conversion_different_rsense():
    """Higher Rsense means more current per CS step."""
    driver_50 = _make_driver(global_scaler=0, rsense_mOhm=50)
    driver_75 = _make_driver(global_scaler=0, rsense_mOhm=75)

    # Higher rsense -> lower max current (V_FS is fixed)
    max_50 = driver_50._convert_cs_to_current(31)
    max_75 = driver_75._convert_cs_to_current(31)
    assert max_50 > max_75

    # Same target current needs higher CS with higher rsense
    target = 1500
    cs_50 = driver_50._convert_current_to_cs(target)
    cs_75 = driver_75._convert_current_to_cs(target)
    assert cs_75 > cs_50


def test_tmc5160_current_exceeds_range_with_low_scaler():
    """Current that fits at full scale should overflow with low scaler."""
    driver = _make_driver(global_scaler=128, rsense_mOhm=50)
    max_current = driver._convert_cs_to_current(31)

    with pytest.raises(ValueError):
        driver._convert_current_to_cs(max_current + 100)


@pytest.mark.parametrize("standstill_mA, gs, rsense, expected_cs, expect_freewheel", [
    # GLOBAL_SCALER=0 (full scale=256), Rsense=50mOhm
    (0,    0, 50,  0, True),
    (500,  0, 50,  2, False),
    (1000, 0, 50,  6, False),
    (1500, 0, 50,  9, False),
    # GLOBAL_SCALER=0 (full scale=256), Rsense=75mOhm
    (0,    0, 75,  0, True),
    (500,  0, 75,  4, False),
    (1000, 0, 75,  9, False),
    # GLOBAL_SCALER=128 (half scale), Rsense=50mOhm
    (0,    128, 50,  0, True),
    (500,  128, 50,  6, False),
    (1000, 128, 50, 13, False),
])
def test_tmc5160_standstill_current_hardcoded(standstill_mA, gs, rsense, expected_cs, expect_freewheel):
    driver = _make_driver(global_scaler=gs, rsense_mOhm=rsense)
    driver.set_current_standstill(standstill_mA)

    assert driver.get_current_standstill() == expected_cs
    assert driver.eval_board.read_register_field(driver.mc.FIELD.IHOLD) == expected_cs
    assert driver.dummy_values.get(driver.motor.AP.FreewheelingMode, 0) == (1 if expect_freewheel else 0)


def test_tmc5160_current_setters_write_ihold_irun_fields():
    driver = _make_driver(global_scaler=0, rsense_mOhm=50)

    driver.set_current(2500)
    driver.set_current_standstill(70)

    assert driver.eval_board.read_register_field(driver.mc.FIELD.IRUN) == driver.get_current()
    assert driver.eval_board.read_register_field(driver.mc.FIELD.IHOLD) == driver.get_current_standstill()


def test_tmc5160_zero_standstill_current_enables_freewheeling():
    driver = _make_driver()

    driver.set_current_standstill(0)

    assert driver.eval_board.read_register_field(driver.mc.FIELD.IHOLD) == 0
    assert driver.dummy_values[driver.motor.AP.FreewheelingMode] == 1


def test_tmc5160_microsteps():
    driver = _make_driver()
    assert driver.get_microsteps() == 16
    assert driver.dummy_values[driver.motor.AP.MicrostepResolution] == 16
    driver.set_microsteps(32)
    assert driver.get_microsteps() == 32
    assert driver.dummy_values[driver.motor.AP.MicrostepResolution] == 32


def test_tmc5160_interpolation_uses_register_field():
    driver = _make_driver()
    driver.set_interpolation(True)
    assert driver.eval_board.read_register_field(driver.mc.FIELD.INTPOL) == 1

    driver.set_interpolation(False)
    assert driver.eval_board.read_register_field(driver.mc.FIELD.INTPOL) == 0


def test_tmc5160_feature_toggles_preserve_disabled_state():
    driver = _make_driver(
        stallguard_enabled=False,
        stallguard_threshold=12,
        coolstep_enabled=False,
        coolstep_threshold=345,
    )

    assert driver.dummy_values[driver.motor.AP.SG2Threshold] == 0
    assert driver.dummy_values[driver.motor.AP.smartEnergyThresholdSpeed] == 0

    driver.set_stallguard_enabled(True)
    driver.set_coolstep_enabled(True)

    assert driver.dummy_values[driver.motor.AP.SG2Threshold] == 12
    assert driver.dummy_values[driver.motor.AP.smartEnergyThresholdSpeed] == 345


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
