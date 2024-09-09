from dataclasses import dataclass

from dip_coater.mechanical.mechanical_setup import MechanicalSetup


@dataclass
class SetupLargeCoater(MechanicalSetup):
    def __init__(self):
        super().__init__(mm_per_revolution=3.0, gearbox_ratio=1.0, steps_per_revolution=200)
