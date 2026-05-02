from dataclasses import dataclass


@dataclass
class MechanicalSetup:
    """Mechanical conversion constants for one lift setup.

    :param mm_per_revolution: Linear travel produced by one motor revolution.
    :param gearbox_ratio: Gear ratio between the motor and the lift drive.
    :param steps_per_revolution: Full motor steps in one motor revolution.
    """

    mm_per_revolution: float
    gearbox_ratio: float = 1.0
    steps_per_revolution: int = 200  # This is typical for many stepper motors

    # ------------ Calculation methods ------------

    def mm_per_step(self, microsteps: int) -> float:
        """Calculate linear travel for one microstep.

        :param microsteps: Microsteps per full step.
        :return: Linear travel in millimeters per microstep.
        """
        return self.mm_per_revolution / (
            self.steps_per_revolution * self.gearbox_ratio * microsteps
        )

    def steps_for_distance(self, distance_mm: float, microsteps: int) -> int:
        """Calculate the nearest whole microstep count for a linear distance.

        :param distance_mm: Linear distance in millimeters.
        :param microsteps: Microsteps per full step.
        :return: Rounded microstep count.
        """
        return round(distance_mm / self.mm_per_step(microsteps))

    def distance_for_steps(self, steps: int, microsteps: int) -> float:
        """Convert a microstep count to linear travel.

        :param steps: Number of microsteps.
        :param microsteps: Microsteps per full step.
        :return: Linear travel in millimeters.
        """
        return steps * self.mm_per_step(microsteps)

    # ------------ Conversion methods ------------

    def mm_to_revs(self, position_mm: float) -> float:
        """Convert linear position to motor revolutions.

        :param position_mm: Linear position or distance in millimeters.
        :return: Motor revolutions.
        """
        return position_mm / self.mm_per_revolution / self.gearbox_ratio

    def revs_to_mm(self, revs: float) -> float:
        """Convert motor revolutions to linear position.

        :param revs: Motor revolutions.
        :return: Linear position or distance in millimeters.
        """
        return revs * self.mm_per_revolution * self.gearbox_ratio

    def steps_to_revs(self, steps: int, microsteps: int) -> float:
        """Convert microsteps to motor revolutions.

        :param steps: Number of microsteps.
        :param microsteps: Microsteps per full step.
        :return: Motor revolutions.
        """
        return steps / (self.steps_per_revolution * microsteps)

    def revs_to_steps(self, revs: float, microsteps: int) -> int:
        """Convert motor revolutions to microsteps.

        :param revs: Motor revolutions.
        :param microsteps: Microsteps per full step.
        :return: Rounded microstep count.
        """
        return round(revs * self.steps_per_revolution * microsteps)

    def mm_to_steps(self, distance_mm: float, microsteps: int) -> int:
        """Convert linear distance to microsteps.

        :param distance_mm: Linear distance in millimeters.
        :param microsteps: Microsteps per full step.
        :return: Rounded microstep count.
        """
        return round(distance_mm / self.mm_per_step(microsteps))

    def steps_to_mm(self, steps: int, microsteps: int) -> float:
        """Convert microsteps to linear distance.

        :param steps: Number of microsteps.
        :param microsteps: Microsteps per full step.
        :return: Linear distance in millimeters.
        """
        return steps * self.mm_per_step(microsteps)

    def mm_s_to_rps(self, velocity_mm_s: float) -> float:
        """Convert linear velocity to rotations per second.

        :param velocity_mm_s: Linear velocity in millimeters per second.
        :return: Rotations per second.
        """
        return velocity_mm_s / self.mm_per_revolution / self.gearbox_ratio

    def rps_to_mm_s(self, rps: float) -> float:
        """Convert rotations per second to linear velocity.

        :param rps: Rotations per second.
        :return: Linear velocity in millimeters per second.
        """
        return rps * self.mm_per_revolution * self.gearbox_ratio

    def rps_to_stepss(self, rps: float, microsteps: int) -> int:
        """Convert rotations per second to microsteps per second.

        :param rps: Rotations per second.
        :param microsteps: Microsteps per full step.
        :return: Rounded microsteps per second.
        """
        return round(rps * self.steps_per_revolution * microsteps)

    def stepss_to_rps(self, stepss: int, microsteps: int) -> float:
        """Convert microsteps per second to rotations per second.

        :param stepss: Microsteps per second.
        :param microsteps: Microsteps per full step.
        :return: Rotations per second.
        """
        return stepss / (self.steps_per_revolution * microsteps)

    def mm_s_to_rpm(self, velocity_mm_s: float) -> float:
        """Convert linear velocity to rotations per minute.

        :param velocity_mm_s: Linear velocity in millimeters per second.
        :return: Rotations per minute.
        """
        return self.mm_s_to_rps(velocity_mm_s) * 60

    def rpm_to_mm_s(self, rpm: float) -> float:
        """Convert rotations per minute to linear velocity.

        :param rpm: Rotations per minute.
        :return: Linear velocity in millimeters per second.
        """
        return self.rps_to_mm_s(rpm / 60)

    def mm_s_to_stepss(self, velocity_mm_s: float, microsteps: int) -> int:
        """Convert linear velocity to microsteps per second.

        :param velocity_mm_s: Linear velocity in millimeters per second.
        :param microsteps: Microsteps per full step.
        :return: Rounded microsteps per second.
        """
        return round(velocity_mm_s / self.mm_per_step(microsteps))

    def stepss_to_mm_s(self, stepss: int, microsteps: int) -> float:
        """Convert microsteps per second to linear velocity.

        :param stepss: Microsteps per second.
        :param microsteps: Microsteps per full step.
        :return: Linear velocity in millimeters per second.
        """
        return stepss * self.mm_per_step(microsteps)

    def mm_s2_to_rpss(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration to rotations per second squared.

        :param acceleration_mm_s2: Linear acceleration in millimeters per second squared.
        :return: Rotations per second squared, or ``None`` for a falsey input.
        """
        return (
            None
            if not acceleration_mm_s2
            else acceleration_mm_s2 / self.mm_per_revolution / self.gearbox_ratio
        )

    def rpss_to_mm_s2(self, rpss: float) -> float:
        """Convert rotations per second squared to linear acceleration.

        :param rpss: Rotations per second squared.
        :return: Linear acceleration in millimeters per second squared, or ``None`` for a falsey input.
        """
        return None if not rpss else rpss * self.mm_per_revolution * self.gearbox_ratio

    def rpss_to_stepss(self, rpss: float, microsteps: int) -> int:
        """Convert rotations per second squared to microsteps per second squared.

        :param rpss: Rotations per second squared.
        :param microsteps: Microsteps per full step.
        :return: Rounded microsteps per second squared, or ``None`` for a falsey input.
        """
        return (
            None
            if not rpss
            else round(rpss * self.steps_per_revolution * microsteps)
        )

    def stepss_to_rpss(self, stepss: int, microsteps: int) -> float:
        """Convert microsteps per second squared to rotations per second squared.

        :param stepss: Microsteps per second squared.
        :param microsteps: Microsteps per full step.
        :return: Rotations per second squared, or ``None`` for a falsey input.
        """
        return None if not stepss else stepss / (self.steps_per_revolution * microsteps)

    def mm_s2_to_rpmm(self, acceleration_mm_s2: float) -> float:
        """Convert linear acceleration to rotations per minute per minute.

        :param acceleration_mm_s2: Linear acceleration in millimeters per second squared.
        :return: Rotations per minute per minute, or ``None`` for a falsey input.
        """
        return (
            None
            if not acceleration_mm_s2
            else self.mm_s2_to_rpss(acceleration_mm_s2) * 3600
        )

    def rpmm_to_mm_s2(self, rpmm: float) -> float:
        """Convert rotations per minute per minute to linear acceleration.

        :param rpmm: Rotations per minute per minute.
        :return: Linear acceleration in millimeters per second squared, or ``None`` for a falsey input.
        """
        return None if not rpmm else self.rpss_to_mm_s2(rpmm / 3600)

    def mm_s2_to_stepss2(self, acceleration_mm_s2: float, microsteps: int) -> int:
        """Convert linear acceleration to microsteps per second squared.

        :param acceleration_mm_s2: Linear acceleration in millimeters per second squared.
        :param microsteps: Microsteps per full step.
        :return: Rounded microsteps per second squared, or ``None`` for a falsey input.
        """
        return (
            None
            if not acceleration_mm_s2
            else round(acceleration_mm_s2 / self.mm_per_step(microsteps))
        )

    def stepss2_to_mm_s2(self, stepss2: int, microsteps: int) -> float:
        """Convert microsteps per second squared to linear acceleration.

        :param stepss2: Microsteps per second squared.
        :param microsteps: Microsteps per full step.
        :return: Linear acceleration in millimeters per second squared, or ``None`` for a falsey input.
        """
        return None if not stepss2 else stepss2 * self.mm_per_step(microsteps)
