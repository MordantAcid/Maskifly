import pytest
from maskinfly.audit import AuditLogger
from maskinfly.masker import Masker

@pytest.fixture
def audit_logger():
    logger = AuditLogger()
    logger.logger.handlers.clear()
    return logger

@pytest.fixture
def masker_with_audit(audit_logger):
    return Masker(audit_enabled=True, audit_logger=audit_logger)

@pytest.fixture
def masker_no_audit():
    return Masker(audit_enabled=False)