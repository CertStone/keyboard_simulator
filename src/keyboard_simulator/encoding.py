"""Utilities for generating text/file typing payloads."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List


CHUNK_SIZE_LINUX = 512
CHUNK_SIZE_WINDOWS = 76


@dataclass(slots=True, frozen=True)
class EncodedFile:
    path: Path
    encoded: str

    @classmethod
    def from_path(cls, path: Path) -> "EncodedFile":
        data = path.read_bytes()
        encoded = base64.b64encode(data).decode("ascii")
        return cls(path=path, encoded=encoded)


def chunk_string(data: str, chunk_size: int) -> List[str]:
    if chunk_size <= 0:  # pragma: no cover - defensive
        raise ValueError("chunk_size must be positive")
    return [data[i : i + chunk_size] for i in range(0, len(data), chunk_size)]


def linux_reconstruction_script(encoded: str, output_filename: str) -> str:
    chunks = chunk_string(encoded, CHUNK_SIZE_LINUX)
    if not chunks:
        raise ValueError("encoded data is empty")
    lines: List[str] = [f"echo -n {chunks[0]} > {output_filename}.b64"]
    for chunk in chunks[1:]:
        lines.append(f"echo -n {chunk} >> {output_filename}.b64")
    lines.extend(
        [
            f"base64 -d {output_filename}.b64 > {output_filename}",
            f"rm {output_filename}.b64",
        ]
    )
    return "\n".join(lines) + "\n"


def windows_reconstruction_script(encoded: str, output_filename: str) -> str:
    chunks = chunk_string(encoded, CHUNK_SIZE_WINDOWS)
    if not chunks:
        raise ValueError("encoded data is empty")
    lines: List[str] = [f"echo {chunks[0]}>tmp.b64"]
    lines.extend(f"echo {chunk}>>tmp.b64" for chunk in chunks[1:])
    lines.append(f"certutil -decode tmp.b64 {output_filename}")
    lines.append("del tmp.b64")
    return "\n".join(lines) + "\n"


def render_script(script: str) -> str:
    """Ensure script uses Windows line endings when needed."""

    return script.replace("\n", "\n")  # placeholder for future customization


def iter_lines(script: str) -> Iterable[str]:
    for line in script.splitlines():
        yield line + "\n"


__all__ = [
    "EncodedFile",
    "chunk_string",
    "linux_reconstruction_script",
    "windows_reconstruction_script",
    "render_script",
    "iter_lines",
]
