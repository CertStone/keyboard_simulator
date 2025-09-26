import base64
import importlib

encoding = importlib.import_module("keyboard_simulator.encoding")


def test_chunk_string():
    data = "ABCDEFGH"
    chunks = encoding.chunk_string(data, 3)
    assert chunks == ["ABC", "DEF", "GH"]


def test_linux_script_trailing_newline(tmp_path):
    payload = "hello world"
    encoded = base64.b64encode(payload.encode()).decode()
    script = encoding.linux_reconstruction_script(encoded, "out.txt")
    assert script.endswith("\n")
    assert "base64 -d" in script
