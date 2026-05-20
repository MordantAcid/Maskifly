import pytest
from unittest.mock import patch
from maskinfly.masker import Masker, HAS_PYDANTIC

pytestmark = pytest.mark.skipif(not HAS_PYDANTIC, reason="pydantic not installed")

# Фикстура с auto_varname=True для тестов, где нужно автоопределение имени
@pytest.fixture
def masker_with_audit(audit_logger):
    return Masker(audit_enabled=True, audit_logger=audit_logger)

@pytest.fixture
def masker_with_auto_varname():
    return Masker(audit_enabled=False, auto_varname=True)

@pytest.fixture
def masker_with_audit_and_auto_varname(audit_logger):
    return Masker(audit_enabled=True, audit_logger=audit_logger, auto_varname=True)

def test_add_pattern(masker_no_audit):
    masker_no_audit.add_pattern("test", r"\d{4}")
    assert masker_no_audit.mask_string("code 1234", "path") == "code ***"

def test_add_pattern_with_custom_replacer(masker_no_audit):
    def my_replacer(match, char, length):
        return "CUSTOM"
    masker_no_audit.add_pattern("custom", r"secret", my_replacer)
    assert masker_no_audit.mask_string("my secret value", "path") == "my CUSTOM value"

def test_from_config_json(tmp_path):
    config = {
        "mask_char": "#",
        "mask_length": 2,
        "patterns": {
            "zip": {"regex": "\\d{5}", "replacer": "full_mask"}
        }
    }
    cfg_file = tmp_path / "config.json"
    import json
    cfg_file.write_text(json.dumps(config))

    masker = Masker.from_config(str(cfg_file))
    assert masker.mask_string("zip 12345", "path") == "zip ##"
    assert masker.mask_char == "#"
    assert masker.mask_length == 2

def test_from_config_yaml(tmp_path):
    pytest.importorskip("yaml")
    config = """
    mask_char: '?'
    mask_length: 3
    patterns:
      test: {regex: '\\d+', replacer: full_mask}
    """
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(config)

    masker = Masker.from_config(str(cfg_file))
    assert masker.mask_string("number 999", "path") == "number ???"

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
            mock_log.assert_called_once_with("path", "varname", "str", value='secret')
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
    # Берём паттерн "password"
    regex, replace_func = masker_with_audit.patterns["password"]
    match = regex.search("password=12345")
    # Применяем функцию замены с параметрами маски
    replaced = replace_func(match, masker_with_audit.mask_char, masker_with_audit.mask_length)
    assert replaced == "password=***"

def test_custom_mask_char_and_length():
    masker = Masker(mask_char='#', mask_length=5)
    assert masker.mask_string("password=123", "path") == "password=#####"
    assert masker.mask_string("user@example.com", "path") == "u#####@example.com"

def test_custom_pattern():
    import re
    def my_replacer(match, char, length):
        return char * length
    custom = {"myid": (re.compile(r'\d{4}'), my_replacer)}
    masker = Masker(custom_patterns=custom)
    assert masker.mask_string("code 1234", "path") == "code ***"

def test_sensitive_key_deep_mask_false():
    """При deep_mask=False чувствительный ключ заменяет всё значение на маску."""
    masker = Masker(deep_mask=False)
    data = {"password": {"user": "admin", "token": "123"}}
    result = masker.mask(data)
    assert result["password"] == "***"

def test_sensitive_key_deep_mask_true():
    masker = Masker(deep_mask=True)
    data = {"password": {"user": "admin", "token": "secret123"}}
    result = masker.mask(data)
    assert "password" in result
    inner = result["password"]
    assert inner["user"] == "admin"   # теперь работает
    assert inner["token"] == "***"
