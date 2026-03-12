from dataclasses import dataclass


@dataclass
class MechanicalSetup:
    mm_per_revolution: float
    gearbox_ratio: float = 1.0
    steps_per_revolution: int = 200  # This is typical for many stepper motors

    # ------------ Calculation methods ------------

    def mm_per_step(self, microsteps: int) -> float:
        return self.mm_per_revolution / (self.steps_per_revolution * self.gearbox_ratio *
                                         microsteps)

    def steps_for_distance(self, distance_mm: float, microsteps: int) -> int:
        return round(distance_mm / self.mm_per_step(microsteps))

    def distance_for_steps(self, steps: int, microsteps: int) -> float:
        return steps * self.mm_per_step(microsteps)

    # ------------ Conversion methods ------------

    def mm_to_revs(self, position_mm: float) -> float:
        """Convert linear position (mm) to revolutions."""
        return position_mm / self.mm_per_revolution / self.gearbox_ratio

    def revs_to_mm(self, revs: float) -> float:
        """Convert revolutions to linear position (mm)."""
        return revs * self.mm_per_revolution * self.gearbox_ratio

    def steps_to_revs(self, steps: int, microsteps: int) -> float:
        """Convert steps to revolutions."""
        return steps / (self.steps_per_revolution * microsteps)

    def revs_to_steps(self, revs: float, microsteps: int) -> int:
        """Convert revolutions to steps."""
        return round(revs * self.steps_per_revolution * microsteps)

    def mm_to_steps(self, distance_mm: float, microsteps: int) -> int:
        """Convert linear distance (mm) to steps."""
        return round(distance_mm / self.mm_per_step(microsteps))

    def steps_to_mm(self, steps: int, microsteps: int) -> float:
        """Convert steps to linear distance (mm)."""
        return steps * self.mm_per_step(microsteps)

    def mm_s_to_rps(self, velocity_mm_s: float) -> float:
        """Convert linear velocity (mm/s) to rotations per second."""
        return velocity_mm_s / self.mm_per_revolution / self.gearbox_ratio

    def rps_to_mm_s(self, rps: float) -> float:
        """Convert rotations per second to linear velocity (mm/s)."""
        return rps * self.mm_per_revolution * self.gearbox_ratio

    def rps_to_stepss(self, rps: float, microsteps: int) -> int:
        """Convert rotations per second to steps per second."""
        return round(rps * self.steps_per_revolution * microsteps)

    def stepss_to_rps(self, stepss: int, microsteps: int) -> float:
        """Convert steps per second to rotations per second."""
        return stepss / (self.steps_per_revolution * microsteps)

    def mm_s_to_rpm(self, velocity_mm_s: float) -> float:
        """Convert linear velocity (mm/s) to rotations per minute."""
        return self.mm_s_to_rps(velocity_mm_s) * 60

    def rpm_to_mm_s(self, rpm: float) -> float:
        """Convert rotations per minute to linear velocity (mm/s)."""
        return self.rps_to_mm_s(rpm / 60)

    def mm_s_to_stepss(self, velocity_mm_s: float, microsteps: int) -> int:
        """Convert linear velocity (mm/s) to steps per second."""
        return round(velocity_mm_s / self.mm_per_step(microsteps))

    def stepss_to_mm_s(self, stepss: int, microsteps: int) -> float:
        """Convert steps per second to linear velocity (mm/s)."""
        return stepss * self.mm_per_step(microsteps)

    def mm_s2_to_rpss(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration (mm/s^2) to rotations per second squared."""
        return None if not acceleration_mm_s2 else (acceleration_mm_s2 / self.mm_per_revolution /
                                                    self.gearbox_ratio)

    def rpss_to_mm_s2(self, rpss: float) -> float:
        """Convert rotations per second squared to linear acceleration (mm/s^2)."""
        return None if not rpss else rpss * self.mm_per_revolution * self.gearbox_ratio

    def rpss_to_stepss(self, rpss: float, microsteps: int) -> int:
        """Convert rotations per second squared to steps per second squared."""
        return None if not rpss else round(rpss * self.steps_per_revolution * microsteps)

    def stepss_to_rpss(self, stepss: int, microsteps: int) -> float:
        """Convert steps per second squared to rotations per second squared."""
        return None if not stepss else stepss / (self.steps_per_revolution * microsteps)

    def mm_s2_to_rpmm(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration (mm/s^2) to rotations per minute per minute."""
        return None if not acceleration_mm_s2 else self.mm_s2_to_rpss(acceleration_mm_s2) * 3600

    def rpmm_to_mm_s2(self, rpmm: float) -> float:
        """Convert rotations per minute per minute to linear acceleration (mm/s^2)."""
        return None if not rpmm else self.rpss_to_mm_s2(rpmm / 3600)

    def mm_s2_to_stepss2(self, acceleration_mm_s2: float, microsteps: int) -> int:
        """Convert linear acceleration (mm/s^2) to steps per second squared."""
        return None if not acceleration_mm_s2 else round(acceleration_mm_s2 /
                                                         self.mm_per_step(microsteps))

    def stepss2_to_mm_s2(self, stepss2: int, microsteps: int) -> float:
        """Convert steps per second squared to linear acceleration (mm/s^2)."""
        return None if not stepss2 else stepss2 * self.mm_per_step(microsteps)
