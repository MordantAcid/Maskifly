import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from maskinfly.cli import main


@pytest.fixture
def sample_json(tmp_path):
    data = {
        "user": "alice",
        "password": "secret123",
        "token": "abc123",
        "nested": {"api_key": "xyz789"}
    }
    file = tmp_path / "input.json"
    file.write_text(json.dumps(data))
    return file


@pytest.fixture
def sample_yaml(tmp_path):
    pytest.importorskip("yaml")
    import yaml

    data = {"user": "bob", "password": "pass", "token": "tok"}
    file = tmp_path / "input.yaml"
    file.write_text(yaml.dump(data))
    return file


def test_mask_command_basic(sample_json, tmp_path, capsys):
    out_file = tmp_path / "out.json"
    # Запуск maskify mask
    sys.argv = ["maskify", "mask", str(sample_json), "-o", str(out_file), "--mask-length", "2"]
    exit_code = main()
    assert exit_code == 0

    # Проверяем выходной файл
    result = json.loads(out_file.read_text())
    assert result["password"] == "**"
    assert result["token"] == "**"
    assert result["user"] == "alice"
    assert result["nested"]["api_key"] == "**"


def test_mask_command_stdout(sample_json, capsys):
    sys.argv = ["maskify", "mask", str(sample_json), "--mask-char", "#"]
    exit_code = main()
    assert exit_code == 0

    captured = capsys.readouterr()
    out_data = json.loads(captured.out)
    assert out_data["password"] == "###"
    assert out_data["token"] == "###"
    assert out_data["nested"]["api_key"] == "###"

def test_mask_command_with_audit(sample_json, caplog):
    import logging
    caplog.set_level(logging.INFO, logger="maskify.audit")
    sys.argv = ["maskify", "mask", str(sample_json), "--audit"]
    exit_code = main()
    assert exit_code == 0

    # Проверяем, что в логах есть записи о маскировке
    assert any("Значение маски" in record.message for record in caplog.records)
    assert any("password" in record.message for record in caplog.records)


def test_mask_command_with_config(tmp_path, sample_json):
    config = {
        "mask_char": "#",
        "mask_length": 4,
        "patterns": {
            "custom": {"regex": "abc123", "replacer": "full_mask"}
        }
    }
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(config))

    out_file = tmp_path / "out.json"
    sys.argv = ["maskify", "mask", str(sample_json), "--config", str(config_file), "-o", str(out_file)]
    exit_code = main()
    assert exit_code == 0

    result = json.loads(out_file.read_text())
    # Стандартные паттерны тоже работают
    assert result["password"] == "####"
    assert result["token"] == "####"  # pattern token (regex) сработал
    # Кастомный паттерн не применится, т.к. "abc123" нет в данных
    assert result["user"] == "alice"


def test_mask_command_deep_mask(tmp_path):
    data = {"password": {"user": "admin", "token": "tok"}}
    in_file = tmp_path / "in.json"
    in_file.write_text(json.dumps(data))

    out_file = tmp_path / "out.json"
    sys.argv = ["maskify", "mask", str(in_file), "--deep-mask", "-o", str(out_file)]
    exit_code = main()
    assert exit_code == 0

    result = json.loads(out_file.read_text())
    assert isinstance(result["password"], dict)
    assert result["password"]["user"] == "admin"
    assert result["password"]["token"] == "***"


def test_check_command_text(sample_json, capsys):
    sys.argv = ["maskify", "check", str(sample_json)]
    exit_code = main()
    assert exit_code == 1  # найдены чувствительные данные
    captured = capsys.readouterr()
    assert "password" in captured.out
    assert "token" in captured.out
    assert "api_key" in captured.out
    assert "пример: secret123" in captured.out


def test_check_command_json(sample_json, capsys):
    sys.argv = ["maskify", "check", str(sample_json), "--format", "json"]
    exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    results = json.loads(captured.out)
    assert len(results) >= 3
    # Находим запись для поля password
    pwd_entry = next((r for r in results if "password" in r["path"]), None)
    assert pwd_entry is not None
    assert pwd_entry["reason"] == "pattern:password" or pwd_entry["reason"] == "sensitive_key"
    # sensitive_key сработает для ключа "password"


def test_check_command_clean(tmp_path):
    data = {"name": "John", "age": 30, "city": "NYC"}
    in_file = tmp_path / "clean.json"
    in_file.write_text(json.dumps(data))

    sys.argv = ["maskify", "check", str(in_file)]
    exit_code = main()
    assert exit_code == 0  # ничего не найдено


def test_mask_yaml_input(sample_yaml, tmp_path, capsys):
    pytest.importorskip("yaml")
    out_file = tmp_path / "out.yaml"
    sys.argv = ["maskify", "mask", str(sample_yaml), "-o", str(out_file)]
    exit_code = main()
    assert exit_code == 0

    import yaml
    result = yaml.safe_load(out_file.read_text())
    assert result["password"] == "***"
    assert result["token"] == "***"


def test_check_yaml_input(sample_yaml, capsys):
    pytest.importorskip("yaml")
    sys.argv = ["maskify", "check", str(sample_yaml)]
    exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "password" in captured.out


def test_file_not_found():
    sys.argv = ["maskify", "mask", "nonexistent.json"]
    exit_code = main()
    assert exit_code == 1


def test_invalid_json(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text("{invalid json")
    sys.argv = ["maskify", "mask", str(bad_file)]
    exit_code = main()
    assert exit_code == 1
