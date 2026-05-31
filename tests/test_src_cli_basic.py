"""
Basic tests for src/cli.py
"""

import pytest


def test_import():
    """Test basic import"""
    from src.cli import __version__
    assert __version__ == "0.2.0"


def test_version():
    """Test version"""
    from src.cli import __version__, __author__
    assert __version__ == "0.2.0"
    assert __author__ == "VOBC"


def test_app_exists():
    """Test app exists"""
    from src.cli import app
    assert app is not None


if __name__ == "__main__":
pytest.main([__file__, "-v"])
