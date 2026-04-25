"""
Compatibility shim for local, uninstalled usage.

The real package lives in ``src/trinamic_wrapper/trinamic_wrapper``. When a
script is executed from ``src/trinamic_wrapper`` directly, Python can resolve
this outer directory as the ``trinamic_wrapper`` package first. Re-export the
inner package so imports like ``from trinamic_wrapper import Direction`` work
without installing the package or setting ``PYTHONPATH``.
"""

from . import trinamic_wrapper as _impl
from .trinamic_wrapper import *  # noqa: F401,F403
from .trinamic_wrapper import __all__ as __all__

# Make ``trinamic_wrapper.<submodule>`` resolve against the real package.
__path__ = _impl.__path__
