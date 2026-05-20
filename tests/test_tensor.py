import inspect
import pytest
from maskinfly.utils import find_variable_name, SENSITIVE_VAR_NAMES

def test_sensitive_var_names():
    assert "password" in SENSITIVE_VAR_NAMES
    assert "token" in SENSITIVE_VAR_NAMES
    assert "api_key" in SENSITIVE_VAR_NAMES

def test_find_variable_name_from_local():
    test_value = "secret123"
    def inner():
        return find_variable_name(test_value, frame_depth=2)
    name = inner()
    assert name == "test_value"

def test_find_variable_name_not_found():
    # Временный объект без имени
    result = find_variable_name(object(), frame_depth=1)
    assert result is None
