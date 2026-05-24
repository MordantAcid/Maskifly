import pytest
import threading
from maskinfly import mask, disabled, Masker

def test_disabled_context():
    """Проверяем, что внутри контекста маскировка не применяется."""
    data = {"password": "secret", "user": "alice"}

    # Обычный вызов – маскировка работает
    assert mask(data)["password"] == "***"

    # Внутри контекста – данные не меняются
    with disabled():
        assert mask(data)["password"] == "secret"

    # После выхода – маскировка снова активна
    assert mask(data)["password"] == "***"


def test_nested_disabled():
    """Вложенные контексты должны корректно восстанавливать состояние."""
    data = {"token": "abc123"}

    with disabled():
        assert mask(data)["token"] == "abc123"
        with disabled():
            assert mask(data)["token"] == "abc123"
        assert mask(data)["token"] == "abc123"
    assert mask(data)["token"] == "***"


def test_disabled_with_masker_instance():
    """Проверяем, что отключение работает и при использовании экземпляра Masker."""
    masker = Masker()
    data = {"password": "secret"}

    assert masker.mask(data)["password"] == "***"

    with disabled():
        assert masker.mask(data)["password"] == "secret"

    assert masker.mask(data)["password"] == "***"


def test_thread_local_disabled():
    """Флаг отключения должен быть изолирован между потоками."""
    data = {"api_key": "key123"}
    results = {}

    def worker(use_disabled: bool):
        if use_disabled:
            with disabled():
                results[threading.current_thread().name] = mask(data)["api_key"]
        else:
            results[threading.current_thread().name] = mask(data)["api_key"]

    t1 = threading.Thread(target=worker, args=(True,), name="disabled_thread")
    t2 = threading.Thread(target=worker, args=(False,), name="enabled_thread")

    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert results["disabled_thread"] == "key123"   # без маскировки
    assert results["enabled_thread"] == "***"       # с маскировкой
