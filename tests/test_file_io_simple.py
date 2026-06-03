"""Simple file I/O tests."""
import json
import tempfile
from pathlib import Path


def test_write_and_read_file():
    """Test writing and reading a file."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
        f.write("hello")
        name = f.name
    with open(name, encoding="utf-8") as rf:
        content = rf.read()
    assert content == "hello"
    Path(name).unlink()

def test_json_file_io():
    """Test JSON file I/O."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump({"a": 1}, f)
        name = f.name
    with open(name, encoding="utf-8") as rf:
        data = json.load(rf)
    assert data["a"] == 1
    Path(name).unlink()
