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
        self._dummy_values[self.AP.PositionReachedFlag] = True

    def move_to(self, steps: int):
        self._dummy_values[self.AP.ActualPosition] = steps
        self._dummy_values[self.AP.PositionReachedFlag] = True


class DummyEvalBoard:
    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values
        self.motors = [DummyMotor(self._dummy_values)]

    def get_axis_parameter(self, parameter, axis):
        return self._dummy_values.get(parameter, 0)


class DummyInterface:
    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values

    def move_by(self, axis, steps: int):
        current = self._dummy_values.get(DummyAxisParameters.ActualPosition, 0)
        self._dummy_values[DummyAxisParameters.ActualPosition] = current + steps
        self._dummy_values[DummyAxisParameters.PositionReachedFlag] = True

    def get_global_parameter(self, parameter, bank):
        return self._dummy_values.get(parameter, 0)

    def set_global_parameter(self, parameter, bank, value):
        self._dummy_values[parameter] = value

    def close(self):
        pass
