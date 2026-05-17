import pytest
from unittest.mock import patch
from maskinfly.masker import Masker, HAS_PYDANTIC

pytestmark = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")

def test_mask_string_by_pattern(masker_no_audit):
    result = masker_no_audit.mask_string("password=12345", "test")
    assert result == "password=***"

def test_mask_string_by_varname(masker_no_audit):
    with patch("maskinfly.masker.find_variable_name", return_value="password"):
        result = masker_no_audit.mask_string("my_secret", "some.path")
        assert result == "***"

def test_mask_string_no_match(masker_no_audit):
    with patch("maskinfly.masker.find_variable_name", return_value=None):
        result = masker_no_audit.mask_string("hello world!", "path")
        assert result == "hello world!"

def test_mask_string_audit(masker_with_audit, audit_logger):
    with patch("maskinfly.masker.find_variable_name", return_value="password"):
        # Подменим audit логгер для проверки вызова
        masker_with_audit.audit = audit_logger
        result = masker_with_audit.mask_string("secret_value", "user.pwd")
        assert result == "***"
        # Проверим, что audit.log был вызван
        with patch.object(audit_logger, "log") as mock_log:
            masker_with_audit.mask_string("secret", "path")
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