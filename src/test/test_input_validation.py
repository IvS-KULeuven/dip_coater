from types import SimpleNamespace

import pytest

from dip_coater.utils.helpers import validated_number_from_submission


def submission(value, *, is_valid):
    return SimpleNamespace(
        input=SimpleNamespace(value=value),
        validation_result=SimpleNamespace(is_valid=is_valid),
    )


def test_invalid_submission_restores_previous_value():
    event = submission("", is_valid=False)

    value = validated_number_from_submission(event, 2.5, float)

    assert value is None
    assert event.input.value == "2.5"


def test_unparseable_submission_is_rejected_even_if_validation_is_missing_it():
    event = submission("not-a-number", is_valid=True)

    value = validated_number_from_submission(event, 7, int)

    assert value is None
    assert event.input.value == "7"


def test_valid_submission_returns_requested_numeric_type():
    event = submission("12.5", is_valid=True)

    value = validated_number_from_submission(event, 2.5, float)

    assert value == pytest.approx(12.5)
    assert isinstance(value, float)
