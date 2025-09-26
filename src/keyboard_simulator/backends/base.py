"""Keyboard backend interface."""

from __future__ import annotations

import abc
from contextlib import AbstractContextManager


class AbstractKeyboardBackend(AbstractContextManager, metaclass=abc.ABCMeta):
    """Interface for sending keyboard events."""

    def __enter__(self):  # pragma: no cover - default implementation
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb):  # pragma: no cover - default implementation
        self.stop()
        return False

    def start(self) -> None:
        """Perform backend specific startup logic."""

    def stop(self) -> None:
        """Perform backend specific teardown logic."""

    @abc.abstractmethod
    def type_character(self, char: str, delay: float) -> None:
        """Type a single character."""

    @abc.abstractmethod
    def press_return(self, delay: float) -> None:
        """Send a newline/enter key event."""

    def flush(self) -> None:
        """Ensure all buffered events are dispatched."""


class BackendError(RuntimeError):
    """Raised when the backend cannot complete an operation."""


__all__ = [
    "AbstractKeyboardBackend",
    "BackendError",
]
