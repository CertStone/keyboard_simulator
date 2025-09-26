"""Keyboard Simulator package."""

from importlib.metadata import version, PackageNotFoundError

from .config import Config, TextConfig, FileConfig, load
from .tasks import build_plan, SimulationPlan, TypingTask
from .simulator import KeyboardSimulator

__all__ = [
    "__version__",
    "Config",
    "TextConfig",
    "FileConfig",
    "load",
    "build_plan",
    "SimulationPlan",
    "TypingTask",
    "KeyboardSimulator",
]

try:
    __version__ = version("keyboard-simulator")
except PackageNotFoundError:  # pragma: no cover - during local development
    __version__ = "0.0.0"
