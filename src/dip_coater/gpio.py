from abc import ABC, abstractmethod

from enum import Enum, IntEnum
import os

class Board(Enum):
    """board"""
    UNKNOWN = 0
    RASPBERRY_PI = 1  # all except Pi 5
    RASPBERRY_PI5 = 2


class GpioState(IntEnum):
    """GPIO value"""
    LOW = 0
    HIGH = 1


class GpioMode(IntEnum):
    """GPIO mode"""
    OUT = 0
    IN = 1


class GpioPUD(IntEnum):
    """Pull up Down"""
    PUD_OFF = 20
    PUD_UP = 22
    PUD_DOWN = 21


class GpioEdge(IntEnum):
    """Edge detection"""
    RISING = 1
    FALLING = 2
    BOTH = 3


class GPIOBase(ABC):
    @abstractmethod
    def setup(self, pin, mode: GpioMode, pull_up_down: GpioPUD = GpioPUD.PUD_OFF, active_state=None):
        pass

    @abstractmethod
    def output(self, pin, state: GpioState):
        pass

    @abstractmethod
    def input(self, pin) -> GpioState:
        pass

    @abstractmethod
    def add_event_detect(self, pin, edge: GpioEdge, callback, bouncetime=None):
        pass

    @abstractmethod
    def add_event_callback(self, pin, callback):
        pass

    @abstractmethod
    def remove_event_detect(self, pin):
        pass

    @abstractmethod
    def cleanup(self):
        pass

class RPiGPIO(GPIOBase):
    def __init__(self):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        self.GPIO.setmode(GPIO.BCM)

    def setup(self, pin, mode: GpioMode, pull_up_down: GpioPUD = GpioPUD.PUD_OFF, active_state=None):
        gpio_mode = self.GPIO.OUT if mode == GpioMode.OUT else self.GPIO.IN
        gpio_pud = {
            GpioPUD.PUD_OFF: self.GPIO.PUD_OFF,
            GpioPUD.PUD_UP: self.GPIO.PUD_UP,
            GpioPUD.PUD_DOWN: self.GPIO.PUD_DOWN
        }[pull_up_down]
        self.GPIO.setup(pin, gpio_mode, pull_up_down=gpio_pud)

    def output(self, pin, state: GpioState):
        self.GPIO.output(pin, state)

    def input(self, pin) -> GpioState:
        return GpioState(self.GPIO.input(pin))

    def add_event_detect(self, pin, edge: GpioEdge, callback, bouncetime=None):
        gpio_edge = {
            GpioEdge.RISING: self.GPIO.RISING,
            GpioEdge.FALLING: self.GPIO.FALLING,
            GpioEdge.BOTH: self.GPIO.BOTH
        }[edge]
        self.GPIO.add_event_detect(pin, gpio_edge, callback=callback, bouncetime=bouncetime)

    def add_event_callback(self, pin, callback):
        self.GPIO.add_event_callback(pin, callback)

    def remove_event_detect(self, pin):
        self.GPIO.remove_event_detect(pin)

    def cleanup(self):
        self.GPIO.cleanup()

class GPIOZero(GPIOBase):
    def __init__(self):
        from gpiozero.pins.lgpio import LGPIOFactory
        from gpiozero import Device
        Device.pin_factory = LGPIOFactory()
        self.pins = {}

    def setup(self, pin, mode: GpioMode, pull_up_down: GpioPUD=GpioPUD.PUD_UP, active_state: GpioState=None):
        from gpiozero import LED, Button
        if mode == GpioMode.OUT:
            self.pins[pin] = LED(pin)
        # Input
        if mode == GpioMode.IN:
            pull_up = True if pull_up_down == GpioPUD.PUD_UP else False if pull_up_down == GpioPUD.PUD_DOWN else None
            active_state_value = True if active_state == GpioState.HIGH else False if active_state == GpioState.LOW else None
            pull_up = pull_up if active_state is None else None    # gpiozero doesn't support pull-up/pull-down when an active state is set
            self.pins[pin] = Button(pin, pull_up=pull_up, active_state=active_state_value)
        # Output
        else:
            self.pins[pin] = LED(pin)

    def output(self, pin, state: GpioState):
        self.pins[pin].on() if state == GpioState.HIGH else self.pins[pin].off()

    def input(self, pin) -> GpioState:
        return GpioState.HIGH if self.pins[pin].is_pressed else GpioState.LOW

    def add_event_detect(self, pin, edge: GpioEdge, callback, bouncetime=None):
        from gpiozero import Button
        if not pin in self.pins:
            raise ValueError(f"Pin {pin} is not set up")
        if callback and not callable(callback):
            raise ValueError("Callback must be callable")
        if not isinstance(self.pins[pin], Button):
            raise ValueError("Event detection can only be added to a button")

        def wrapped_callback():
            callback(pin)

        if edge == GpioEdge.RISING:
            self.pins[pin].when_pressed = wrapped_callback
        elif edge == GpioEdge.FALLING:
            self.pins[pin].when_released = wrapped_callback
        elif edge == GpioEdge.BOTH:
            self.pins[pin].when_pressed = wrapped_callback
            self.pins[pin].when_released = wrapped_callback

        if bouncetime and hasattr(self.pins[pin], 'bounce_time'):
            self.pins[pin].bounce_time = bouncetime / 1000.0  # Convert to seconds

    def add_event_callback(self, pin, callback):
        # In gpiozero, we can't add multiple callbacks, so we'll combine them
        existing_callback = self.pins[pin].when_pressed

        def combined_callback():
            if existing_callback:
                existing_callback()
            callback()

        self.pins[pin].when_pressed = combined_callback
        self.pins[pin].when_released = combined_callback

    def remove_event_detect(self, pin):
        from gpiozero import Button
        self.pins[pin].when_pressed = None
        self.pins[pin].when_released = None
        if hasattr(self.pins[pin], 'bounce_time'):
            self.pins[pin].bounce_time = None

    def cleanup(self):
        for pin in self.pins.values():
            pin.close()

class DummyGPIO(GPIOBase):
    def __init__(self):
        self.pins = {}
        self.events = {}
        self.callbacks = {}

    def setup(self, pin, mode: GpioMode, pull_up_down: GpioPUD = GpioPUD.PUD_OFF, active_state=None):
        self.pins[pin] = GpioState.HIGH if active_state == GpioState.LOW else GpioState.LOW

    def output(self, pin, state: GpioState):
        self.pins[pin] = state
        print(f"Pin {pin} set to {state.name}")

    def input(self, pin) -> GpioState:
        return self.pins.get(pin, GpioState.LOW)

    def add_event_detect(self, pin, edge: GpioEdge, callback, bouncetime=None):
        self.events[pin] = edge
        if callback:
            self.callbacks[pin] = [callback]
        print(f"Event detection added to pin {pin} for edge {edge.name}")

    def add_event_callback(self, pin, callback):
        if pin in self.callbacks:
            self.callbacks[pin].append(callback)
        else:
            self.callbacks[pin] = [callback]
        print(f"Callback added to pin {pin}")

    def remove_event_detect(self, pin):
        if pin in self.events:
            del self.events[pin]
        if pin in self.callbacks:
            del self.callbacks[pin]
        print(f"Event detection removed from pin {pin}")

    def cleanup(self):
        self.pins.clear()
        print("GPIO cleaned up")


def get_board_type():
    if not os.path.exists('/proc/device-tree/model'):
        return Board.UNKNOWN

    with open('/proc/device-tree/model', encoding="utf-8") as f:
        model = f.readline().lower()
        if "raspberry pi 5" in model:
            return Board.RASPBERRY_PI5
        elif "raspberry" in model:
            return Board.RASPBERRY_PI
        else:
            return Board.UNKNOWN


def get_gpio_instance():
    """
    Get the GPIO instance based on the board type.
    !!! This function should be called only once in the application !!!
    """
    board = get_board_type()
    print(f"Detected board type: {board}")

    if board == Board.RASPBERRY_PI5:
        print("Attempting to use GPIOZero for Raspberry Pi 5")
        try:
            import gpiozero
            return GPIOZero()
        except ImportError as err:
            print(f"ImportError: {err}")
            print("Board is Raspberry Pi 5 but module gpiozero isn't installed.")
            print("Follow the installation instructions: https://gpiozero.readthedocs.io/en/stable/installing.html")
            raise
    elif board == Board.RASPBERRY_PI:
        print("Attempting to use RPi.GPIO for Raspberry Pi")
        try:
            import RPi.GPIO
            return RPiGPIO()
        except ImportError as err:
            print(f"ImportError: {err}")
            print("Board is Raspberry Pi but module RPi.GPIO isn't installed.")
            print("Follow the installation instructions: https://sourceforge.net/p/raspberry-gpio-python/wiki/install")
            raise
    else:
        print("Unknown board or not running on a Raspberry Pi. Using dummy implementation.")
        return DummyGPIO()


''' Usage
gpio = get_gpio_instance()
gpio.setup(18, GpioMode.OUT)
gpio.output(18, GpioState.HIGH)
gpio.cleanup()
'''

if __name__ == "__main__":
    gpio = get_gpio_instance()
    print("Testing GPIO pin 19")
    gpio.setup(19, GpioMode.IN)
    print(gpio.input(19))
    gpio.cleanup()
    print("Done")
