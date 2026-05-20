import json
import logging
import pytest
from maskinfly.audit import AuditLogger

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
