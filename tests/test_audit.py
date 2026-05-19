import json
from maskinfly.audit import AuditLogger

def test_audit_json_format(capsys):
    logger = AuditLogger(format='json')
    logger.log("path", "pattern", "str", value="secret123")
    # Лог выводится через logging, перехватываем через capsys
    # проще проверить через caplog
    pass  # реализовать с caplog

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
