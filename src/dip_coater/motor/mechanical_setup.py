from dataclasses import dataclass


@dataclass
class MechanicalSetup:
    mm_per_revolution: float
    gearbox_ratio: float = 1.0
    steps_per_revolution: int = 200  # This is typical for many stepper motors

    # ------------ Calculation methods ------------

    def mm_per_step(self, microsteps: int) -> float:
        return self.mm_per_revolution / (self.steps_per_revolution * self.gearbox_ratio * microsteps)

    def steps_for_distance(self, distance_mm: float, microsteps: int) -> int:
        return round(distance_mm / self.mm_per_step(microsteps))

    def distance_for_steps(self, steps: int, microsteps: int) -> float:
        return steps * self.mm_per_step(microsteps)

    # ------------ Conversion methods ------------

    def mm_to_rot(self, position_mm: float) -> float:
        """Convert linear position (mm) to rotations."""
        return position_mm / self.mm_per_revolution / self.gearbox_ratio

    def rot_to_mm(self, rotations: float) -> float:
        """Convert rotations to linear position (mm)."""
        return rotations * self.mm_per_revolution * self.gearbox_ratio

    def mm_s_to_rps(self, velocity_mm_s: float) -> float:
        """Convert linear velocity (mm/s) to rotations per second."""
        return velocity_mm_s / self.mm_per_revolution / self.gearbox_ratio

    def rps_to_mm_s(self, rps: float) -> float:
        """Convert rotations per second to linear velocity (mm/s)."""
        return rps * self.mm_per_revolution * self.gearbox_ratio

    def mm_s_to_rpm(self, velocity_mm_s: float) -> float:
        """Convert linear velocity (mm/s) to rotations per minute."""
        return self.mm_s_to_rps(velocity_mm_s) * 60

    def rpm_to_mm_s(self, rpm: float) -> float:
        """Convert rotations per minute to linear velocity (mm/s)."""
        return self.rps_to_mm_s(rpm / 60)

    def mm_s2_to_rpss(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration (mm/s^2) to rotations per second squared."""
        return acceleration_mm_s2 / self.mm_per_revolution / self.gearbox_ratio

    def rpss_to_mm_s2(self, rpss: float) -> float:
        """Convert rotations per second squared to linear acceleration (mm/s^2)."""
        return rpss * self.mm_per_revolution * self.gearbox_ratio

    def mm_s2_to_rpmm(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration (mm/s^2) to rotations per minute per minute."""
        return self.mm_s2_to_rpss(acceleration_mm_s2) * 3600

    def rpmm_to_mm_s2(self, rpmm: float) -> float:
        """Convert rotations per minute per minute to linear acceleration (mm/s^2)."""
        return self.rpss_to_mm_s2(rpmm / 3600)

    def steps_to_rot(self, steps: int, microsteps: int) -> float:
        """Convert steps to rotations."""
        return steps / (self.steps_per_revolution * microsteps)

    def rot_to_steps(self, rotations: float, microsteps: int) -> int:
        """Convert rotations to steps."""
        return round(rotations * self.steps_per_revolution * microsteps)
