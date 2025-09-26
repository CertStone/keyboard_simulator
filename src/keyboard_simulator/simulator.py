"""High level orchestrator for typing tasks."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Callable, Optional, Iterable

from .backends.base import AbstractKeyboardBackend
from .tasks import SimulationPlan, TypingTask

CountdownCallback = Callable[[int], None]
StateCallback = Callable[[str], None]


@dataclass(slots=True)
class SimulatorHooks:
    on_countdown: Optional[CountdownCallback] = None
    on_status: Optional[StateCallback] = None


class KeyboardSimulator:
    def __init__(self, backend: AbstractKeyboardBackend, hooks: Optional[SimulatorHooks] = None):
        self.backend = backend
        self.hooks = hooks or SimulatorHooks()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

    def stop(self) -> None:
        self.stop_event.set()
        self.pause_event.set()

    def pause(self) -> None:
        self.pause_event.clear()
        if self.hooks.on_status:
            self.hooks.on_status("paused")

    def resume(self) -> None:
        self.pause_event.set()
        if self.hooks.on_status:
            self.hooks.on_status("running")

    def _handle_countdown(self, countdown: int) -> bool:
        for seconds_left in range(countdown, 0, -1):
            if self.stop_event.is_set():
                return False
            if self.hooks.on_countdown:
                self.hooks.on_countdown(seconds_left)
            time.sleep(1)
        return True

    def run_plan(self, plan: SimulationPlan) -> None:
        self.stop_event.clear()
        self.pause_event.set()
        if not self._handle_countdown(plan.countdown_before_start):
            return
        if self.hooks.on_status:
            self.hooks.on_status("running")

        with self.backend:
            for task in plan.tasks:
                self._execute_task(task, plan.delay_between_keystrokes)
                if self.stop_event.is_set():
                    break

        if self.hooks.on_status:
            self.hooks.on_status("stopped" if self.stop_event.is_set() else "completed")

    def _execute_task(self, task: TypingTask, delay: float) -> None:
        for char in task.payload:
            if self.stop_event.is_set():
                break
            while not self.pause_event.is_set():
                if self.stop_event.is_set():
                    break
                time.sleep(0.1)
            if self.stop_event.is_set():
                break
            self.backend.type_character(char, delay)

    def iter_characters(self, plan: SimulationPlan) -> Iterable[str]:
        for task in plan.tasks:
            for char in task.payload:
                yield char


__all__ = ["KeyboardSimulator", "SimulatorHooks"]
