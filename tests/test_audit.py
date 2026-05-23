import json
import logging
import pytest
import asyncio
import time

from unittest.mock import AsyncMock, Mock
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

@pytest.mark.asyncio
async def test_async_mode_log_non_blocking(caplog):
    """Проверяем, что log() в асинхронном режиме не блокирует и запись в итоге появляется."""
    caplog.set_level(logging.INFO, logger="maskify.audit")
    logger = AuditLogger(format='text', async_mode=True, queue_maxsize=1)
    start = time.perf_counter()
    logger.log("path", "reason", "str", value="test")
    elapsed = time.perf_counter() - start
    # Постановка в очередь должна быть быстрой
    assert elapsed < 0.01
    # Даём время фоновому потоку обработать
    time.sleep(0.2)
    logger.stop()
    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert "Значение маски 'path'" in record.getMessage()

@pytest.mark.asyncio
async def test_async_mode_custom_async_handler():
    """Передаём асинхронный обработчик и проверяем, что он вызывается."""
    entries = []
    async def async_handler(entry):
        entries.append(entry)

    logger = AuditLogger(async_mode=True, async_handler=async_handler, queue_maxsize=1)
    logger.log("pwd", "varname", "str", value="secret", app_name="test")
    # Даём время фоновому потоку обработать
    await asyncio.sleep(0.2)
    logger.stop()
    assert len(entries) == 1
    entry = entries[0]
    # В безопасном режиме (по умолчанию False) должны быть все поля
    assert entry["path"] == "pwd"
    assert entry["reason"] == "varname"
    assert entry["type"] == "str"
    assert "hash" in entry

@pytest.mark.asyncio
async def test_async_mode_queue_full():
    """При заполненной очереди log() не блокируется и запись отбрасывается."""
    processed = []

    def handler(entry):
        processed.append(entry)

    logger = AuditLogger(async_mode=True, queue_maxsize=1, custom_handler=handler)
    # Заполняем очередь
    logger._queue.put_nowait({"dummy": "entry"})
    # Следующая запись должна быть отброшена без ошибки
    logger.log("path", "reason", "str", value="value")
    # Останавливаем и дожидаемся обработки
    logger.stop(timeout=1.0)
    # Должна быть обработана только первая запись (dummy)
    assert len(processed) == 1
    assert processed[0] == {"dummy": "entry"}

@pytest.mark.asyncio
async def test_async_mode_stop_waits_for_empty_queue():
    """stop() дожидается обработки всех записей."""
    processed = 0
    async def slow_handler(entry):
        nonlocal processed
        await asyncio.sleep(0.1)
        processed += 1

    logger = AuditLogger(async_mode=True, async_handler=slow_handler, queue_maxsize=0)
    for i in range(3):
        logger.log(f"path{i}", "reason", "str", value="x")
    # Останавливаем с таймаутом
    logger.stop(timeout=1.0)
    assert processed == 3

def test_async_mode_not_used_in_sync_mode():
    """Если async_mode=False, очередь и поток не создаются."""
    logger = AuditLogger(async_mode=False)
    assert not hasattr(logger, '_queue')
    assert not hasattr(logger, '_thread')
    logger.log("path", "reason", "str", value="test")
    # Никаких исключений
