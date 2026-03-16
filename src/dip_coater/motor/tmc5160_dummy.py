class DummyAxisParameters:
    TargetPosition = "TargetPosition"
    ActualPosition = "ActualPosition"
    TargetVelocity = "TargetVelocity"
    ActualVelocity = "ActualVelocity"
    MaxVelocity = "MaxVelocity"
    MaxAcceleration = "MaxAcceleration"
    MaxCurrent = "MaxCurrent"
    StandbyCurrent = "StandbyCurrent"
    PositionReachedFlag = "PositionReachedFlag"
    RightEndstop = "RightEndstop"
    LeftEndstop = "LeftEndstop"
    AutomaticRightStop = "AutomaticRightStop"
    AutomaticLeftStop = "AutomaticLeftStop"
    SW_MODE = "SW_MODE"
    A1 = "A1"
    V1 = "V1"
    MaxDeceleration = "MaxDeceleration"
    D1 = "D1"
    StartVelocity = "StartVelocity"
    StopVelocity = "StopVelocity"
    RampWaitTime = "RampWaitTime"
    THIGH = "THIGH"
    VDCMIN = "VDCMIN"
    HighSpeedChopperMode = "HighSpeedChopperMode"
    HighSpeedFullstepMode = "HighSpeedFullstepMode"
    MeasuredSpeed = "MeasuredSpeed"
    I_scale_analog = "I_scale_analog"
    internal_Rsense = "internal_Rsense"
    MicrostepResolution = "MicrostepResolution"
    ChopperBlankTime = "ChopperBlankTime"
    ConstantTOffMode = "ConstantTOffMode"
    DisableFastDecayComparator = "DisableFastDecayComparator"
    ChopperHysteresisEnd = "ChopperHysteresisEnd"
    ChopperHysteresisStart = "ChopperHysteresisStart"
    TOff = "TOff"
    SEIMIN = "SEIMIN"
    SECDS = "SECDS"
    smartEnergyHysteresis = "smartEnergyHysteresis"
    SECUS = "SECUS"
    smartEnergyHysteresisStart = "smartEnergyHysteresisStart"
    SG2FilterEnable = "SG2FilterEnable"
    SG2Threshold = "SG2Threshold"
    smartEnergyActualCurrent = "smartEnergyActualCurrent"
    smartEnergyStallVelocity = "smartEnergyStallVelocity"
    smartEnergyThresholdSpeed = "smartEnergyThresholdSpeed"
    RandomTOffMode = "RandomTOffMode"
    ChopperSynchronization = "ChopperSynchronization"
    PWMThresholdSpeed = "PWMThresholdSpeed"
    PWMGrad = "PWMGrad"
    PWMAmplitude = "PWMAmplitude"
    PWMFrequency = "PWMFrequency"
    PWMAutoscale = "PWMAutoscale"
    FreewheelingMode = "FreewheelingMode"
    LoadValue = "LoadValue"
    EncoderPosition = "EncoderPosition"
    EncoderResolution = "EncoderResolution"
    Intpol = "Intpol"


class DummyRegisters:
    GCONF = 0x00
    GSTAT = 0x01
    IFCNT = 0x02
    SLAVECONF = 0x03
    IOIN_OUTPUT = 0x04
    X_COMPARE = 0x05
    OTP_PROG = 0x06
    OTP_READ = 0x07
    FACTORY_CONF = 0x08
    SHORT_CONF = 0x09
    DRV_CONF = 0x0A
    GLOBAL_SCALER = 0x0B
    OFFSET_READ = 0x0C
    IHOLD_IRUN = 0x10
    TPOWERDOWN = 0x11
    TSTEP = 0x12
    TPWMTHRS = 0x13
    TCOOLTHRS = 0x14
    THIGH = 0x15
    RAMPMODE = 0x20
    XACTUAL = 0x21
    VACTUAL = 0x22
    VSTART = 0x23
    A1 = 0x24
    V1 = 0x25
    AMAX = 0x26
    VMAX = 0x27
    DMAX = 0x28
    D1 = 0x2A
    VSTOP = 0x2B
    TZEROWAIT = 0x2C
    XTARGET = 0x2D
    VDCMIN = 0x33
    SW_MODE = 0x34
    RAMP_STAT = 0x35
    XLATCH = 0x36
    ENCMODE = 0x38
    X_ENC = 0x39
    ENC_CONST = 0x3A
    ENC_STATUS = 0x3B
    ENC_LATCH = 0x3C
    ENC_DEVIATION = 0x3D
    MSLUT0 = 0x60
    MSLUT1 = 0x61
    MSLUT2 = 0x62
    MSLUT3 = 0x63
    MSLUT4 = 0x64
    MSLUT5 = 0x65
    MSLUT6 = 0x66
    MSLUT7 = 0x67
    MSLUTSEL = 0x68
    MSLUTSTART = 0x69
    MSCNT = 0x6A
    MSCURACT = 0x6B
    CHOPCONF = 0x6C
    COOLCONF = 0x6D
    DCCTRL = 0x6E
    DRV_STATUS = 0x6F
    PWM_CONF = 0x70
    PWM_SCALE = 0x71
    PWM_AUTO = 0x72
    LOST_STEPS = 0x73


class DummyFields:
    # GLOBAL_SCALER: (address, mask, shift)
    GLOBAL_SCALER = (0x0B, 0x000000FF, 0)
    # IHOLD_IRUN
    IHOLD = (0x10, 0x0000001F, 0)
    IRUN = (0x10, 0x00001F00, 8)
    IHOLDDELAY = (0x10, 0x000F0000, 16)
    # RAMP_STAT
    POSITION_REACHED = (0x35, 0x00000200, 9)
    # CHOPCONF
    MRES = (0x6C, 0x0F000000, 24)
    INTPOL = (0x6C, 0x10000000, 28)
    CHM = (0x6C, 0x00004000, 14)
    TOFF = (0x6C, 0x0000000F, 0)
    TBL = (0x6C, 0x00018000, 15)
    VSENSE = (0x6C, 0x00020000, 17)
    VHIGHFS = (0x6C, 0x00040000, 18)
    VHIGHCHM = (0x6C, 0x00080000, 19)
    RNDTF = (0x6C, 0x00002000, 13)
    TPFD = (0x6C, 0x00F00000, 20)
    # COOLCONF
    SEMIN = (0x6D, 0x0000000F, 0)
    SEUP = (0x6D, 0x00000060, 5)
    SEMAX = (0x6D, 0x00000F00, 8)
    SEDN = (0x6D, 0x00006000, 13)
    SEIMIN = (0x6D, 0x00008000, 15)
    SGT = (0x6D, 0x007F0000, 16)
    SFILT = (0x6D, 0x01000000, 24)
    # DRV_STATUS
    SG_RESULT = (0x6F, 0x000003FF, 0)
    CS_ACTUAL = (0x6F, 0x001F0000, 16)
    STALLGUARD = (0x6F, 0x01000000, 24)
    # GCONF
    EN_PWM_MODE = (0x00, 0x00000004, 2)
    SHAFT = (0x00, 0x00000010, 4)


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

    def set_axis_parameter(self, parameter, value):
        self._dummy_values[parameter] = value

    def get_axis_parameter(self, parameter, axis=0):
        return self._dummy_values.get(parameter, 0)


class DummyTMC5160IC:
    REG = DummyRegisters
    FIELD = DummyFields


class DummyEvalBoard:
    def __init__(self, dummy_values: dict, register_values: dict):
        self._dummy_values = dummy_values
        self._register_values = register_values
        self.motors = [DummyMotor(self._dummy_values)]
        self.ics = [DummyTMC5160IC()]

    def get_axis_parameter(self, parameter, axis):
        return self._dummy_values.get(parameter, 0)

    def write_register(self, register_address, value):
        self._register_values[register_address] = value

    def read_register(self, register_address, signed=False):
        return self._register_values.get(register_address, 0)

    def write_register_field(self, field, value):
        address, mask, shift = field
        current = self._register_values.get(address, 0)
        current = (current & ~mask) | ((value << shift) & mask)
        self._register_values[address] = current

    def read_register_field(self, field):
        address, mask, shift = field
        current = self._register_values.get(address, 0)
        return (current & mask) >> shift


class DummyInterface:
    def __init__(self, dummy_values: dict):
        self._dummy_values = dummy_values

    def move_by(self, axis, steps: int):
        current = self._dummy_values.get(DummyAxisParameters.ActualPosition, 0)
        self._dummy_values[DummyAxisParameters.ActualPosition] = current + steps
        self._dummy_values[DummyAxisParameters.PositionReachedFlag] = True

    def rotate(self, motor, value):
        pass

    def stop(self, motor):
        self._dummy_values[DummyAxisParameters.PositionReachedFlag] = True

    def move_to(self, motor, position, module_id=1):
        self._dummy_values[DummyAxisParameters.ActualPosition] = position
        self._dummy_values[DummyAxisParameters.PositionReachedFlag] = True

    def get_global_parameter(self, parameter, bank):
        return self._dummy_values.get(parameter, 0)

    def set_global_parameter(self, parameter, bank, value):
        self._dummy_values[parameter] = value

    def close(self):
        pass
