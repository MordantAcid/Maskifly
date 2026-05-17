import pytest
from unittest.mock import patch
from maskinfly import mask, Masker, AuditLogger, __version__

def test_mask_function_with_dict():
    result = mask({"user": "alice", "password": "pass123"})
    assert result["password"] == "***"
    assert result["user"] == "alice"

def test_mask_function_with_string():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    result = mask(f"My token is {jwt}")
    assert result == "My token is ***"

def test_mask_function_with_audit(caplog):
    caplog.set_level("INFO", logger="maskify.audit")
    mask({"secret": "abc"}, audit_enabled=True)
    assert len(caplog.records) > 0
    record = caplog.records[0]
    assert "Значение маски 'secret'" in record.message
    assert "reason=varname" in record.message
    assert "type=str" in record.message

def test_mask_function_custom_audit_logger():
    custom_logger = AuditLogger()
    with patch.object(custom_logger, "log") as mock_log:
        mask("token=xyz", audit_enabled=True, audit_logger=custom_logger)
        mock_log.assert_called()