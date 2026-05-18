import logging
import pytest
from maskinfly.audit import AuditLogger

def test_audit_logger_creates_handler():
    logger = AuditLogger()
    assert len(logger.logger.handlers) == 1
    assert isinstance(logger.logger.handlers[0], logging.Handler)

def test_audit_logger_respects_provided_logger():
    custom_logger = logging.getLogger("custom")
    custom_logger.handlers.clear()
    logger = AuditLogger(logger=custom_logger)
    assert logger.logger is custom_logger
    assert len(logger.logger.handlers) == 0

def test_audit_logger_log(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger()
    logger.log("user.password", "pattern", "str")

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Значение маски 'user.password'" in record.message
    assert "reason=pattern" in record.message
    assert "type=str" in record.message
