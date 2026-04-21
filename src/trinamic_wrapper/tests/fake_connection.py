"""Test fixtures: fake eval board + connection for offline unit tests."""

from __future__ import annotations

from unittest.mock import MagicMock


class FakeConnection:
    """Records all TMCL-style calls so tests can assert on them."""

    def __init__(self) -> None:
        self.axis_parameters: dict[tuple[int, int], int] = {}
        self.registers: dict[int, int] = {}
        self.calls: list[tuple[str, tuple]] = []

    # ---- axis parameters (used by set_axis_parameter on the motor) ------
    def set_axis_parameter(self, ap_type, axis, value, module_id):
        self.calls.append(("set_ap", (ap_type, axis, value, module_id)))
        self.axis_parameters[(ap_type, axis)] = value

    def get_axis_parameter(self, ap_type, axis, module_id, signed=False):
        self.calls.append(("get_ap", (ap_type, axis, module_id, signed)))
        return self.axis_parameters.get((ap_type, axis), 0)

    # ---- register access -------------------------------------------------
    def write_mc(self, register, value, module_id):
        self.calls.append(("write_mc", (register, value, module_id)))
        self.registers[register] = value

    def read_mc(self, register, module_id, signed=False):
        self.calls.append(("read_mc", (register, module_id, signed)))
        return self.registers.get(register, 0)

    def write_drv(self, register, value, module_id):
        self.calls.append(("write_drv", (register, value, module_id)))
        self.registers[register] = value

    def read_drv(self, register, module_id, signed=False):
        self.calls.append(("read_drv", (register, module_id, signed)))
        return self.registers.get(register, 0)

    # ---- motion ----------------------------------------------------------
    def rotate(self, motor, velocity, module_id=None):
        self.calls.append(("rotate", (motor, velocity, module_id)))

    def stop(self, motor, module_id=None):
        self.calls.append(("stop", (motor, module_id)))

    def move_to(self, motor, position, module_id=None):
        self.calls.append(("move_to", (motor, position, module_id)))

    def move_by(self, motor, delta, module_id=None):
        self.calls.append(("move_by", (motor, delta, module_id)))

    # ---- utility ---------------------------------------------------------
    def last(self, kind: str):
        for k, args in reversed(self.calls):
            if k == kind:
                return args
        return None

    def get_ap(self, ap_type, axis=0):
        return self.axis_parameters.get((ap_type, axis), 0)
