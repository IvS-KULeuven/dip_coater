import pytest

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


@pytest.fixture
def geared_setup():
    return MechanicalSetup(
        mm_per_revolution=4.0,
        gearbox_ratio=2.0,
        steps_per_revolution=200,
    )


def test_distance_revolution_conversion_matches_step_conversion(geared_setup):
    distance_mm = 4.0
    microsteps = 16

    revolutions_via_steps = geared_setup.steps_to_revs(
        geared_setup.mm_to_steps(distance_mm, microsteps), microsteps
    )

    assert geared_setup.mm_to_revs(distance_mm) == pytest.approx(2.0)
    assert geared_setup.mm_to_revs(distance_mm) == pytest.approx(
        revolutions_via_steps
    )
    assert geared_setup.revs_to_mm(revolutions_via_steps) == pytest.approx(
        distance_mm
    )


def test_velocity_revolution_conversion_matches_step_conversion(geared_setup):
    velocity_mm_s = 4.0
    microsteps = 16

    rps_via_steps = geared_setup.stepss_to_rps(
        geared_setup.mm_s_to_stepss(velocity_mm_s, microsteps), microsteps
    )

    assert geared_setup.mm_s_to_rps(velocity_mm_s) == pytest.approx(rps_via_steps)
    assert geared_setup.rps_to_mm_s(rps_via_steps) == pytest.approx(velocity_mm_s)


def test_acceleration_revolution_conversion_matches_step_conversion(geared_setup):
    acceleration_mm_s2 = 4.0
    microsteps = 16

    rpss_via_steps = geared_setup.stepss_to_rpss(
        geared_setup.mm_s2_to_stepss2(acceleration_mm_s2, microsteps), microsteps
    )

    assert geared_setup.mm_s2_to_rpss(acceleration_mm_s2) == pytest.approx(
        rpss_via_steps
    )
    assert geared_setup.rpss_to_mm_s2(rpss_via_steps) == pytest.approx(
        acceleration_mm_s2
    )


@pytest.mark.parametrize(
    ("overrides", "field_name"),
    [
        ({"mm_per_revolution": 0.0}, "mm_per_revolution"),
        ({"mm_per_revolution": -1.0}, "mm_per_revolution"),
        ({"mm_per_revolution": float("nan")}, "mm_per_revolution"),
        ({"mm_per_revolution": float("inf")}, "mm_per_revolution"),
        ({"gearbox_ratio": 0.0}, "gearbox_ratio"),
        ({"gearbox_ratio": -1.0}, "gearbox_ratio"),
        ({"gearbox_ratio": float("nan")}, "gearbox_ratio"),
        ({"steps_per_revolution": 0}, "steps_per_revolution"),
        ({"steps_per_revolution": -200}, "steps_per_revolution"),
        ({"steps_per_revolution": 200.5}, "steps_per_revolution"),
    ],
)
def test_mechanical_setup_rejects_invalid_conversion_constants(
    overrides, field_name
):
    values = {
        "mm_per_revolution": 4.0,
        "gearbox_ratio": 1.0,
        "steps_per_revolution": 200,
    }
    values.update(overrides)

    with pytest.raises(ValueError, match=field_name):
        MechanicalSetup(**values)
