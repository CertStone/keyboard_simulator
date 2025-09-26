import importlib
from pathlib import Path

config = importlib.import_module("keyboard_simulator.config")
tasks = importlib.import_module("keyboard_simulator.tasks")


def test_build_plan_text():
    cfg = config.TextConfig(
        text_to_type="abc", delay_between_keystrokes=0.1, countdown_before_start=1
    )
    plan = tasks.build_plan(cfg)
    assert plan.total_characters == 3
    assert plan.tasks[0].payload == "abc"


def test_build_plan_file(tmp_path: Path):
    file_path = tmp_path / "hello.txt"
    file_path.write_text("hello", encoding="utf-8")
    cfg = config.FileConfig(
        file_path=file_path,
        target_os="linux",
        output_filename="hello.txt",
        delay_between_keystrokes=0.01,
        countdown_before_start=1,
    )
    plan = tasks.build_plan(cfg)
    assert plan.tasks[0].description.startswith("文件传输")
    assert "base64 -d" in plan.tasks[0].payload
