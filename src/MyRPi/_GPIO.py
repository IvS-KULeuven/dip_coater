LOW = None
HIGH =None
IN = None
OUT = None
BCM = None
BOARD = None
PUD_UP = None
PUD_DOWN = None
RISING = None
FALLING = None
BOTH = None

def output(*args, **kwargs):
    ...

def input(*args, **kwargs):
    return 1

def setmode(*args, **kwargs):
    ...

def setwarnings(flag: bool):
    ...

def setup(*args, **kwargs):
    ...

def cleanup():
    ...

def add_event_callback (channel, callback):
    ...

def add_event_detect (channel, edge, callback=None, bouncetime=None):
    ...

def remove_event_detect (channel):
    ...
