import threading
import pytest
from maskinfly import mask, disabled, Masker

def test_masking_in_threads():
    """Маскировка в нескольких потоках одновременно."""
    data = {"password": "secret"}
    results = {}

    def worker(worker_id):
        results[worker_id] = mask(data)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    for res in results.values():
        assert res["password"] == "***"


def test_disabled_context_is_thread_local():
    """Флаг отключения маскировки не распространяется между потоками."""
    data = {"token": "abc123"}
    results = {}

    def worker_with_disabled():
        with disabled():
            results["disabled"] = mask(data)

    def worker_without_disabled():
        results["enabled"] = mask(data)

    t1 = threading.Thread(target=worker_with_disabled)
    t2 = threading.Thread(target=worker_without_disabled)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["disabled"]["token"] == "abc123"
    assert results["enabled"]["token"] == "***"


def test_concurrent_masker_instances():
    """Несколько экземпляров Masker в разных потоках не мешают друг другу."""
    masker1 = Masker(mask_char="#", mask_length=2)
    masker2 = Masker(mask_char="X", mask_length=5)

    data = {"password": "value"}
    results = {}

    def worker(masker, result_key):
        results[result_key] = masker.mask(data)

    t1 = threading.Thread(target=worker, args=(masker1, "m1"))
    t2 = threading.Thread(target=worker, args=(masker2, "m2"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["m1"]["password"] == "##"
    assert results["m2"]["password"] == "XXXXX"


def test_audit_logger_thread_safety():
    """Проверяем, что асинхронный аудит с очередью потокобезопасен."""
    from maskinfly.audit import AuditLogger
    import logging
    import time

    logger = logging.getLogger("thread_audit")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    audit = AuditLogger(logger=logger, async_mode=True, queue_maxsize=100, drop_on_full=True)
    masker = Masker(audit_enabled=True, audit_logger=audit)

    def worker():
        for _ in range(100):
            masker.mask({"password": "secret"})

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    audit.stop(timeout=2.0)
