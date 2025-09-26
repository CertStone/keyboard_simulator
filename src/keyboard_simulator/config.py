"""Configuration models and helpers for keyboard simulator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Literal, Optional
import json


class Mode(str, Enum):
    """Supported automation modes."""

    TEXT = "text"
    FILE = "file"


TargetOS = Literal["windows", "linux"]


@dataclass(slots=True)
class BaseConfig:
    delay_between_keystrokes: float = 0.01
    countdown_before_start: int = 5


@dataclass(slots=True)
class TextConfig(BaseConfig):
    text_to_type: str = ""

    @property
    def mode(self) -> Mode:
        return Mode.TEXT


@dataclass(slots=True)
class FileConfig(BaseConfig):
    file_path: Path = Path()
    target_os: TargetOS = "linux"
    output_filename: str = "output"

    @property
    def mode(self) -> Mode:
        return Mode.FILE


Config = TextConfig | FileConfig


class ConfigError(Exception):
    """Raised when config parsing fails."""


def _validate_float(value: Any, field_name: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ConfigError(f"'{field_name}' 必须是数值类型") from exc


def _validate_int(value: Any, field_name: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ConfigError(f"'{field_name}' 必须是整数") from exc


def _resolve_path(raw_path: str, field_name: str) -> Path:
    if not raw_path:
        raise ConfigError(f"'{field_name}' 不能为空")
    path = Path(raw_path).expanduser()
    if not path.exists():
        raise ConfigError(f"'{field_name}' 指向的文件不存在: {path}")
    return path


def _parse_common(data: Dict[str, Any]) -> Dict[str, Any]:
    delay = _validate_float(data.get("delay_between_keystrokes", 0.01), "delay_between_keystrokes")
    countdown = _validate_int(data.get("countdown_before_start", 5), "countdown_before_start")
    if countdown < 0:
        raise ConfigError("'countdown_before_start' 必须是非负整数")
    if delay < 0:
        raise ConfigError("'delay_between_keystrokes' 必须是非负数")
    return {
        "delay_between_keystrokes": delay,
        "countdown_before_start": countdown,
    }


def from_dict(data: Dict[str, Any], *, base_path: Optional[Path] = None) -> Config:
    """Parse config dictionary into a Config dataclass."""

    if not data:
        raise ConfigError("配置数据为空")

    try:
        mode = Mode(data["mode"])
    except KeyError as exc:
        raise ConfigError("缺少 'mode' 字段") from exc
    except ValueError as exc:
        raise ConfigError("'mode' 仅支持 'text' 或 'file'") from exc

    common_kwargs = _parse_common(data)

    if mode is Mode.TEXT:
        text = data.get("text_to_type", "")
        if not isinstance(text, str):
            raise ConfigError("'text_to_type' 必须是字符串")
        return TextConfig(text_to_type=text, **common_kwargs)

    # file mode
    raw_path = data.get("file_path")
    if not isinstance(raw_path, str):
        raise ConfigError("'file_path' 必须是字符串")
    path = Path(raw_path)
    if base_path and not path.is_absolute():
        path = (base_path / path).resolve()
    file_path = _resolve_path(str(path), "file_path")

    target_os = data.get("target_os", "linux")
    if target_os not in ("windows", "linux"):
        raise ConfigError("'target_os' 仅支持 'windows' 或 'linux'")

    output_filename = data.get("output_filename")
    if not output_filename:
        raise ConfigError("'output_filename' 不能为空")

    return FileConfig(
        file_path=file_path,
        target_os=target_os,
        output_filename=str(output_filename),
        **common_kwargs,
    )


def load(path: Path) -> Config:
    """Load configuration from a JSON file."""

    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ConfigError(f"未找到配置文件: {path}") from exc

    try:
        data: Dict[str, Any] = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"解析 JSON 失败: {exc}") from exc

    return from_dict(data, base_path=path.parent)


__all__ = [
    "Mode",
    "Config",
    "TextConfig",
    "FileConfig",
    "TargetOS",
    "ConfigError",
    "from_dict",
    "load",
]
