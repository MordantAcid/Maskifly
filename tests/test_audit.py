import json
import logging
import pytest
import asyncio
import time

from unittest.mock import AsyncMock, Mock
from maskinfly.audit import AuditLogger

def test_audit_logger_initialization():
    logger = AuditLogger()
    assert logger.logger.name == "maskify.audit"
    assert logger.format == "text"

def test_audit_logger_sync_log(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format="text")
    logger.log("path", "reason", "str", value="test")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Значение маски 'path'" in record.getMessage()
    assert "reason=reason" in record.getMessage()
    assert "type=str" in record.getMessage()

def test_audit_logger_json_format(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format="json")
    logger.log("path", "reason", "str", value="test")
    record = caplog.records[0]
    log_entry = json.loads(record.getMessage())
    assert log_entry["path"] == "path"
    assert log_entry["reason"] == "reason"
    assert log_entry["type"] == "str"
    assert "hash" in log_entry

def test_audit_logger_custom_handler():
    entries = []
    def handler(entry):
        entries.append(entry)
    logger = AuditLogger(custom_handler=handler)
    logger.log("path", "reason", "str", value="test")
    assert len(entries) == 1
    assert entries[0]["path"] == "path"
    assert entries[0]["reason"] == "reason"

def test_audit_logger_safe_mode(caplog):
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(safe_mode=True)
    logger.log("secret_path", "varname", "str", value="sensitive")
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "secret_path" not in record.getMessage()
    assert "sensitive" not in record.getMessage()
    assert "hash=" in record.getMessage()
    assert "path" not in record.getMessage()

@pytest.mark.asyncio
async def test_async_mode_log_non_blocking(caplog):
    """Проверяем, что log() в асинхронном режиме не блокирует и запись в итоге появляется."""
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format='text', async_mode=True, queue_maxsize=1, drop_on_full=True)
    start = time.perf_counter()
    logger.log("path", "reason", "str", value="test")
    elapsed = time.perf_counter() - start
    assert elapsed < 0.01
    await asyncio.sleep(0.2)
    logger.stop()
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Значение маски 'path'" in record.getMessage()

@pytest.mark.asyncio
async def test_async_mode_custom_async_handler():
    entries = []
    async def async_handler(entry):
        entries.append(entry)

    logger = AuditLogger(async_mode=True, async_handler=async_handler, queue_maxsize=1, drop_on_full=True)
    logger.log("pwd", "varname", "str", value="secret", app_name="test")
    await asyncio.sleep(0.2)
    logger.stop()
    assert len(entries) == 1
    entry = entries[0]
    assert entry["path"] == "pwd"
    assert entry["reason"] == "varname"
    assert entry["type"] == "str"
    assert "hash" in entry

@pytest.mark.asyncio
async def test_async_mode_queue_full():
    processed = []
    def handler(entry):
        processed.append(entry)

    # Устанавливаем drop_on_full=True, чтобы при переполнении очереди событие гарантированно отбрасывалось
    logger = AuditLogger(async_mode=True, queue_maxsize=1, custom_handler=handler, drop_on_full=True)
    logger._queue.put_nowait({"dummy": "entry"})
    logger.log("path", "reason", "str", value="value")
    logger.stop(timeout=1.0)
    assert len(processed) == 1

@pytest.mark.asyncio
async def test_async_mode_stop_waits_for_empty_queue():
    processed = 0
    async def slow_handler(entry):
        nonlocal processed
        await asyncio.sleep(0.1)
        processed += 1

    logger = AuditLogger(async_mode=True, async_handler=slow_handler, queue_maxsize=0, drop_on_full=True)
    for i in range(3):
        logger.log(f"path{i}", "reason", "str", value="x")
    logger.stop(timeout=1.0)
    assert processed == 3

def test_async_mode_not_used_in_sync_mode():
    logger = AuditLogger(async_mode=False)
    assert not hasattr(logger, '_queue')
    assert not hasattr(logger, '_thread')
    logger.log("path", "reason", "str", value="test")
