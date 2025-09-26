"""Interception driver backend implementation."""

from __future__ import annotations

import time
from typing import Optional, Any

from .base import AbstractKeyboardBackend, BackendError

try:  # pragma: no cover - optional dependency during CI
    import interception
    from interception import _keycodes as keycodes
except ModuleNotFoundError:  # pragma: no cover - fallback for non-Windows envs
    interception = None
    keycodes = None


class InterceptionBackend(AbstractKeyboardBackend):
    """Backend backed by the interception-python driver."""

    def __init__(self, context: Optional[Any] = None, device: Optional[int] = None):
        if interception is None:
            raise BackendError("interception-python 未安装，无法使用该后端")
        context_cls = getattr(interception, "Interception")
        self.context = context or context_cls()
        self.device = device
        self._own_context = context is None

    def start(self) -> None:
        if self.device is not None:
            return

        filter_flag = getattr(interception, "FilterKeyFlag")
        self.context.set_filter(self.context.is_keyboard, filter_flag.FILTER_KEY_ALL)
        for idx in range(20):
            if self.context.is_keyboard(idx):
                self.device = idx
                break
        if self.device is None:
            raise BackendError("未找到可用的键盘设备")

    def stop(self) -> None:
        if self._own_context:
            self.context.destroy()

    def _send_stroke(self, scan_code: int, is_extended: bool, state: Any) -> None:
        if self.device is None:
            raise BackendError("键盘设备尚未初始化")
        key_stroke_cls = getattr(interception, "KeyStroke")
        stroke = key_stroke_cls(scan_code, state)
        if is_extended:
            key_flag = getattr(interception, "KeyFlag")
            stroke.flags |= key_flag.KEY_E0
        self.context.send(self.device, stroke)

    def _press_key_data(self, key_data: Any, delay: float) -> None:
        if keycodes is None:
            raise BackendError("无法访问 interception 键码表")
        modifiers = []
        if key_data.shift:
            modifiers.append(keycodes.get_key_information("shift"))
        if key_data.ctrl:
            modifiers.append(keycodes.get_key_information("ctrl"))
        if key_data.alt:
            modifiers.append(keycodes.get_key_information("alt"))

        key_flag = getattr(interception, "KeyFlag")

        for mod in modifiers:
            self._send_stroke(mod.scan_code, mod.is_extended, key_flag.KEY_DOWN)
            if delay > 0:
                time.sleep(delay / 2)

        self._send_stroke(key_data.scan_code, key_data.is_extended, key_flag.KEY_DOWN)
        if delay > 0:
            time.sleep(delay)
        self._send_stroke(key_data.scan_code, key_data.is_extended, key_flag.KEY_UP)

        for mod in reversed(modifiers):
            if delay > 0:
                time.sleep(delay / 2)
            self._send_stroke(mod.scan_code, mod.is_extended, key_flag.KEY_UP)

    def type_character(self, char: str, delay: float) -> None:
        if char == "\n":
            self.press_return(delay)
            return
        if keycodes is None:
            raise BackendError("无法访问 interception 键码表")
        unknown_error = getattr(keycodes, "UnknownKeyError", Exception)
        try:
            key_data = keycodes.get_key_information(char)
        except unknown_error as exc:  # type: ignore[arg-type]
            raise BackendError(f"无法处理字符: {char}") from exc
        self._press_key_data(key_data, delay)
        if delay > 0:
            time.sleep(delay)

    def press_return(self, delay: float) -> None:
        if keycodes is None:
            raise BackendError("无法访问 interception 键码表")
        enter_info = keycodes.get_key_information("enter")
        self._press_key_data(enter_info, delay)


__all__ = ["InterceptionBackend"]
