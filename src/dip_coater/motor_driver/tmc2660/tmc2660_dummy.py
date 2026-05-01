import time


class DummyAxisParameters:
    PositionReachedFlag = "PositionReachedFlag"
    MicrostepResolution = "MicrostepResolution"
    VSense = "VSense"
    MaxCurrent = "MaxCurrent"
    StandbyCurrent = "StandbyCurrent"
    MaxVelocity = "MaxVelocity"
    MaxAcceleration = "MaxAcceleration"
    ActualPosition = "ActualPosition"
    StepDirSource = "StepDirSource"
    ConstantTOffMode = "ConstantTOffMode"
    ChopperHysteresisStart = "ChopperHysteresisStart"
    ChopperHysteresisEnd = "ChopperHysteresisEnd"
    ChopperBlankTime = "ChopperBlankTime"
    TOff = "TOff"
    Intpol = "Intpol"
    SG2Threshold = "SG2Threshold"
    SG2FilterEnable = "SG2FilterEnable"
    LoadValue = "LoadValue"
    SEIMIN = "SEIMIN"
    SECDS = "SECDS"
    SECUS = "SECUS"
    smartEnergyHysteresis = "smartEnergyHysteresis"
    smartEnergyThresholdSpeed = "smartEnergyThresholdSpeed"
    smartEnergyActualCurrent = "smartEnergyActualCurrent"


class DummyGlobalParameters:
    DriversEnable = "DriversEnable"


class DummyLandungsbruecke:
    GP = DummyGlobalParameters


class DummyMotor:
    AP = DummyAxisParameters

    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values

    def stop(self):
        _update_motion_state(self._dummy_values)
        _clear_motion(self._dummy_values)
        self._dummy_values[self.AP.PositionReachedFlag] = True

    def move_to(self, steps: int):
        _start_motion(self._dummy_values, steps)


class DummyEvalBoard:
    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values
        self.motors = [DummyMotor(self._dummy_values)]

    def get_axis_parameter(self, parameter, axis):
        _update_motion_state(self._dummy_values)
        return self._dummy_values.get(parameter, 0)


class DummyInterface:
    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values

    def move_by(self, axis, steps: int):
        _update_motion_state(self._dummy_values)
        current = self._dummy_values.get(DummyAxisParameters.ActualPosition, 0)
        _start_motion(self._dummy_values, current + steps)

    def get_global_parameter(self, parameter, bank):
        return self._dummy_values.get(parameter, 0)

    def set_global_parameter(self, parameter, bank, value):
        self._dummy_values[parameter] = value

    def close(self):
        pass


_MOTION_START_TIME = "_motion_start_time_s"
_MOTION_START_POSITION = "_motion_start_position"
_MOTION_TARGET_POSITION = "_motion_target_position"
_MOTION_DURATION = "_motion_duration_s"


def _start_motion(dummy_values: dict, target_position: int) -> None:
    current_position = dummy_values.get(DummyAxisParameters.ActualPosition, 0)
    distance_steps = target_position - current_position
    max_velocity = abs(dummy_values.get(DummyAxisParameters.MaxVelocity, 0))
    if distance_steps == 0 or max_velocity <= 0:
        dummy_values[DummyAxisParameters.ActualPosition] = target_position
        dummy_values[DummyAxisParameters.PositionReachedFlag] = True
        _clear_motion(dummy_values)
        return
    dummy_values[_MOTION_START_TIME] = time.monotonic()
    dummy_values[_MOTION_START_POSITION] = current_position
    dummy_values[_MOTION_TARGET_POSITION] = target_position
    dummy_values[_MOTION_DURATION] = abs(distance_steps) / max_velocity
    dummy_values[DummyAxisParameters.PositionReachedFlag] = False


def _update_motion_state(dummy_values: dict) -> None:
    target_position = dummy_values.get(_MOTION_TARGET_POSITION)
    if target_position is None:
        return
    start_time = dummy_values.get(_MOTION_START_TIME)
    duration_s = dummy_values.get(_MOTION_DURATION, 0)
    if start_time is None or duration_s <= 0:
        _finish_motion(dummy_values)
        return
    elapsed_s = time.monotonic() - start_time
    if elapsed_s >= duration_s:
        _finish_motion(dummy_values)
        return
    progress = max(0.0, elapsed_s / duration_s)
    start_position = dummy_values.get(_MOTION_START_POSITION, 0)
    travel_steps = target_position - start_position
    dummy_values[DummyAxisParameters.ActualPosition] = round(
        start_position + travel_steps * progress
    )
    dummy_values[DummyAxisParameters.PositionReachedFlag] = False


def _finish_motion(dummy_values: dict) -> None:
    target_position = dummy_values.get(_MOTION_TARGET_POSITION)
    if target_position is not None:
        dummy_values[DummyAxisParameters.ActualPosition] = target_position
    dummy_values[DummyAxisParameters.PositionReachedFlag] = True
    _clear_motion(dummy_values)


def _clear_motion(dummy_values: dict) -> None:
    dummy_values.pop(_MOTION_START_TIME, None)
    dummy_values.pop(_MOTION_START_POSITION, None)
    dummy_values.pop(_MOTION_TARGET_POSITION, None)
    dummy_values.pop(_MOTION_DURATION, None)
