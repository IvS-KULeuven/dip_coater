import pytest

from dip_coater.gpio import GPIOZero, GpioEdge, GpioMode, GpioPUD, GpioState


class FakePin:
    def __init__(self, state):
        self.state = state


class FakeButton:
    def __init__(self, pin, pull_up=None, active_state=None):
        self.number = pin
        self.pull_up = pull_up
        self.active_state = (not pull_up) if active_state is None else active_state
        self.pin = FakePin(not self.active_state)
        self.when_pressed = None
        self.when_released = None
        self.bounce_time = None
        self.closed = False

    @property
    def is_pressed(self):
        return self.pin.state == self.active_state

    def press(self):
        self.pin.state = self.active_state
        if self.when_pressed:
            self.when_pressed(self)

    def release(self):
        self.pin.state = not self.active_state
        if self.when_released:
            self.when_released(self)

    def close(self):
        self.closed = True


class FakeLED:
    created = 0

    def __init__(self, pin):
        type(self).created += 1
        self.pin = pin
        self.value = 0
        self.closed = False

    def on(self):
        self.value = 1

    def off(self):
        self.value = 0

    def close(self):
        self.closed = True


@pytest.fixture
def gpio():
    FakeLED.created = 0
    return GPIOZero(button_class=FakeButton, led_class=FakeLED)


def test_output_setup_constructs_one_led(gpio):
    gpio.setup(17, GpioMode.OUT)

    assert FakeLED.created == 1
    assert isinstance(gpio.pins[17], FakeLED)


def test_input_returns_raw_electrical_level_for_pull_up_button(gpio):
    gpio.setup(19, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)
    button = gpio.pins[19]

    assert button.is_pressed is False
    assert gpio.input(19) == GpioState.HIGH

    button.press()

    assert button.is_pressed is True
    assert gpio.input(19) == GpioState.LOW


@pytest.mark.parametrize(
    ("edge", "expected_transitions"),
    [
        (GpioEdge.RISING, ["release"]),
        (GpioEdge.FALLING, ["press"]),
        (GpioEdge.BOTH, ["press", "release"]),
    ],
)
def test_event_detection_uses_electrical_edges(gpio, edge, expected_transitions):
    gpio.setup(19, GpioMode.IN, pull_up_down=GpioPUD.PUD_UP)
    button = gpio.pins[19]
    transitions = []
    gpio.add_event_detect(
        19,
        edge,
        callback=lambda pin: transitions.append(
            "press" if gpio.input(pin) == GpioState.LOW else "release"
        ),
        bouncetime=25,
    )

    button.press()
    button.release()

    assert transitions == expected_transitions
    assert button.bounce_time == pytest.approx(0.025)
