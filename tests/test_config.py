import importlib
import json
from pathlib import Path

import pytest

cfg = importlib.import_module("keyboard_simulator.config")


def test_load_text_config(tmp_path: Path) -> None:
    data = {
        "mode": "text",
        "text_to_type": "hello",
        "delay_between_keystrokes": 0.05,
        "countdown_before_start": 2,
    }
    file_path = tmp_path / "config.json"
    file_path.write_text(json.dumps(data), encoding="utf-8")

    loaded = cfg.load(file_path)
    assert isinstance(loaded, cfg.TextConfig)
    assert loaded.text_to_type == "hello"
    assert loaded.delay_between_keystrokes == 0.05
    assert loaded.countdown_before_start == 2


def test_invalid_mode_raises() -> None:
    with pytest.raises(cfg.ConfigError):
        cfg.from_dict({"mode": "invalid"})
