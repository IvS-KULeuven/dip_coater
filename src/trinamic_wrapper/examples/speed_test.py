from trinamic_wrapper import connection, create_motor, MotorConfig, StepMode, Direction, Chip
import time

with connection("/dev/tty.usbmodemTMCEVAL1") as conn:
    motor = create_motor(Chip.TMC5160, conn,
        config=MotorConfig(full_steps_per_rev=200, sense_resistor_ohms=0.075))
    motor.set_step_mode(StepMode.USTEP_256)
    motor.set_run_current_mA(1500)
    motor.set_standstill_current_mA(100)
    motor.set_acceleration_rps2(5.0)

    if motor.has_feature("stealthchop"):
        motor.set_stealthchop(True, threshold_rps=3.0)
    if motor.has_feature("interpolation"):
        motor.set_interpolation(True)

    motor.enable()
    motor.reset_position()

    speed_rps = 0.1
    motor.rotate(speed_rps=speed_rps, direction=Direction.CW)
    time.sleep(5.0)                    # run for exactly 5 s
    motor.stop()
    time.sleep(0.5)
    pos = motor.get_actual_position_rot()
    motor.disable()

print(f"expected {speed_rps*5.0:.3f}5 rev, got {pos:.3f} rev  ->  actual speed = {pos/5:.3f} rot/s")
