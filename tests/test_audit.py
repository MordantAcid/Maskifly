import json
import logging
import pytest

from maskinfly.audit import AuditLogger

def test_audit_safe_mode_text(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format='text', safe_mode=True)
    logger.log("path", "pattern", "str", value="secret123")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    # В безопасном режиме сообщение не должно содержать path, reason, type
    assert "path" not in record.getMessage()
    assert "pattern" not in record.getMessage()
    assert "str" not in record.getMessage()
    assert "hash=" in record.getMessage()
    # Проверяем, что хеш имеет длину 8 символов
    assert len(record.getMessage().split("hash=")[1]) == 8

def test_audit_safe_mode_json(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format='json', safe_mode=True)
    logger.log("path", "pattern", "str", value="secret123")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    log_entry = json.loads(record.getMessage())
    assert "timestamp" in log_entry
    assert "hash" in log_entry
    assert "path" not in log_entry
    assert "reason" not in log_entry
    assert "type" not in log_entry

def test_audit_safe_mode_custom_handler():
    entries = []
    def handler(entry):
        entries.append(entry)
    logger = AuditLogger(custom_handler=handler, safe_mode=True)
    logger.log("pwd", "varname", "str", value="123", app_name="test")
    assert len(entries) == 1
    entry = entries[0]
    assert "timestamp" in entry
    assert "hash" in entry
    assert "path" not in entry
    assert "reason" not in entry
    assert "type" not in entry
    # app_name не должен попадать в безопасном режиме
    assert "app_name" not in entry

def test_audit_json_format(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format='json')
    logger.log("path", "pattern", "str", value="secret123")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    # Проверяем, что запись — JSON
    log_entry = json.loads(record.getMessage())
    assert log_entry["path"] == "path"
    assert log_entry["reason"] == "pattern"
    assert log_entry["type"] == "str"
    assert "hash" in log_entry

def test_audit_custom_handler():
    entries = []
    def handler(entry):
        entries.append(entry)
    logger = AuditLogger(custom_handler=handler, app_name="test_app")
    logger.log("pwd", "varname", "str", value="123", app_name="override")
    assert len(entries) == 1
    assert entries[0]["path"] == "pwd"
    assert entries[0]["app_name"] == "override"
    assert "hash" in entries[0]
