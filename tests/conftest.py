"""pytest fixtures for wiki parser tests"""

import pytest
import tempfile
from pathlib import Path

from src.wiki.parser import PythonParser


@pytest.fixture
def parser(tmp_path):
    """Create a PythonParser instance with a temp root path"""
    return PythonParser(root_path=str(tmp_path))


@pytest.fixture
def temp_py_file(tmp_path):
    """Create a temporary Python file and return its path"""
    def _create_file(content: str, name: str = "test_module.py") -> Path:
        file_path = tmp_path / name
        file_path.write_text(content, encoding="utf-8")
        return file_path
    return _create_file


@pytest.fixture
def sample_module_code():
    """Return a sample Python module with classes, functions, imports"""
    return '''"""
Sample module docstring
"""

import os
import sys
from typing import Optional, List

class BaseClass:
    """Base class docstring"""
    
    def __init__(self):
        self.value = 42
    
    def public_method(self):
        """Public method"""
        pass
    
    def _private_method(self):
        """Private method"""
        pass

class DerivedClass(BaseClass):
    """Derived class"""
    
    attribute: int = 10
    
    def method(self, x: int) -> int:
        """Method with args and return"""
        return x

def standalone_function(x: int, y: str) -> bool:
    """Standalone function"""
    return True

def _private_function():
    """Private function"""
    pass
'''


@pytest.fixture
def class_only_code():
    """Code with only a class definition"""
    return '''"""
Class only module
"""

class SimpleClass:
    """A simple class"""
    
    def method1(self):
        pass
    
    def _hidden(self):
        pass
'''


@pytest.fixture
def function_only_code():
    """Code with only function definitions"""
    return '''"""
Function only module
"""

def func1(a, b):
    """Function 1"""
    pass

@decorator
def func2():
    """Decorated function"""
    pass
'''


@pytest.fixture
def imports_only_code():
    """Code with only imports"""
    return '''"""
Imports only
"""

import os
import sys as system
from typing import List, Dict
from collections import OrderedDict as OD
'''


@pytest.fixture
def docstring_only_code():
    """Code with only docstring"""
    return '''"""
This module has only a docstring.
"""
'''


@pytest.fixture
def empty_file_code():
    """Empty file content"""
    return ''


@pytest.fixture
def comments_only_code():
    """File with only comments (will cause SyntaxError)"""
    return '''# This is just a comment
# Another comment
'''


@pytest.fixture
def binary_content():
    """Binary content that can't be decoded as UTF-8"""
    return b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
