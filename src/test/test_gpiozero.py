from gpiozero import Button
from gpiozero.pins.lgpio import LGPIOFactory
from gpiozero import Device
import time

# Set up the LGPIOFactory for Raspberry Pi 5
Device.pin_factory = LGPIOFactory()

# Set up pin 19 as an input
button = Button(19)

print("GPIO Input Test Script for Raspberry Pi 5")
print("Reading input on pin 19")
print("Press Ctrl+C to exit")

def callback_pressed():
    print("Callback pressed!")

def callback_released(button):
    print(f"Callback released! {button.pin}")

try:
    # Keep track of the last state to only print when it changes
    last_state = button.is_pressed
    button.when_pressed = callback_pressed
    button.when_released = callback_released

    while True:
        current_state = button.is_pressed

        if current_state != last_state:
            if current_state:
                print("Button pressed (HIGH)")
            else:
                print("Button released (LOW)")

            last_state = current_state

        time.sleep(0.1)  # Small delay to prevent CPU overuse

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    # Clean up
    button.close()