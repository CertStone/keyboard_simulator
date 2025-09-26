"""Transform configuration into executable typing tasks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from . import config as cfg
from .encoding import EncodedFile, linux_reconstruction_script, windows_reconstruction_script


@dataclass(slots=True)
class TypingTask:
    description: str
    payload: str


@dataclass(slots=True)
class SimulationPlan:
    delay_between_keystrokes: float
    countdown_before_start: int
    tasks: List[TypingTask]

    @property
    def total_characters(self) -> int:
        return sum(len(task.payload) for task in self.tasks)


def build_plan(config: cfg.Config) -> SimulationPlan:
    if isinstance(config, cfg.TextConfig):
        task = TypingTask(description="文本输入", payload=config.text_to_type)
        return SimulationPlan(
            delay_between_keystrokes=config.delay_between_keystrokes,
            countdown_before_start=config.countdown_before_start,
            tasks=[task],
        )

    # FileConfig
    encoded = EncodedFile.from_path(config.file_path)
    if config.target_os == "linux":
        payload = linux_reconstruction_script(encoded.encoded, config.output_filename)
        description = "文件传输 - Linux"
    else:
        payload = windows_reconstruction_script(encoded.encoded, config.output_filename)
        description = "文件传输 - Windows"

    task = TypingTask(description=description, payload=payload)
    return SimulationPlan(
        delay_between_keystrokes=config.delay_between_keystrokes,
        countdown_before_start=config.countdown_before_start,
        tasks=[task],
    )


__all__ = [
    "TypingTask",
    "SimulationPlan",
    "build_plan",
]
