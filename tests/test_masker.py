import pytest
from unittest.mock import patch
from maskinfly.masker import Masker, HAS_PYDANTIC

pytestmark = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")

# Фикстура с auto_varname=True для тестов, где нужно автоопределение имени
@pytest.fixture
def masker_with_auto_varname():
    return Masker(audit_enabled=False, auto_varname=True)

@pytest.fixture
def masker_with_audit_and_auto_varname(audit_logger):
    return Masker(audit_enabled=True, audit_logger=audit_logger, auto_varname=True)

def test_mask_string_by_pattern(masker_no_audit):
    result = masker_no_audit.mask_string("password=12345", "test")
    assert result == "password=***"

def test_mask_string_by_varname(masker_with_auto_varname):
    """Маскировка по имени переменной работает только при auto_varname=True."""
    with patch("maskinfly.masker.find_variable_name", return_value="password"):
        result = masker_with_auto_varname.mask_string("my_secret", "some.path")
        assert result == "***"

def test_mask_string_by_varname_disabled(masker_no_audit):
    """При auto_varname=False имя переменной не ищется → маскировки нет."""
    with patch("maskinfly.masker.find_variable_name", return_value="password"):
        result = masker_no_audit.mask_string("my_secret", "some.path")
        assert result == "my_secret"  # не замаскировано

def test_mask_string_by_explicit_var_name(masker_no_audit):
    """Явный var_name работает даже при auto_varname=False."""
    result = masker_no_audit.mask_string("my_secret", "some.path", var_name="password")
    assert result == "***"

def test_mask_string_audit(masker_with_audit_and_auto_varname, audit_logger):
    with patch("maskinfly.masker.find_variable_name", return_value="password"):
        # Подменим audit логгер для проверки вызова
        masker_with_audit_and_auto_varname.audit = audit_logger
        result = masker_with_audit_and_auto_varname.mask_string("secret_value", "user.pwd")
        assert result == "***"
        with patch.object(audit_logger, "log") as mock_log:
            masker_with_audit_and_auto_varname.mask_string("secret", "path")
            mock_log.assert_called_once_with("path", "varname", "str")

def test_mask_dict(masker_no_audit):
    data = {
        "user": "john",
        "password": "secret123",
        "nested": {"api_key": "abc123"}
    }
    masked = masker_no_audit.mask(data)
    assert masked["password"] == "***"
    assert masked["nested"]["api_key"] == "***"
    assert masked["user"] == "john"

def test_mask_list(masker_no_audit):
    data = ["token=xyz", "safe", {"pwd": "pass"}]
    masked = masker_no_audit.mask(data)
    assert masked[0] == "token=***"
    assert masked[1] == "safe"
    assert masked[2]["pwd"] == "***"

def test_mask_secret_str(masker_no_audit):
    from pydantic import SecretStr
    secret = SecretStr("real_secret")
    masked = masker_no_audit.mask(secret, path="secret_field")
    assert masked == "***"

def test_mask_other_type(masker_no_audit):
    assert masker_no_audit.mask(42) == 42
    assert masker_no_audit.mask(True) is True
    assert masker_no_audit.mask(None) is None

def test_mask_replacer(masker_with_audit):
    pattern = masker_with_audit.patterns["password"]
    match = pattern.search("password=12345")
    replaced = masker_with_audit._replacer(match)
    assert replaced == "password=***"
