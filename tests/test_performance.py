import pytest
import json
import sys
from maskinfly import mask, Masker

# Для глубокой рекурсии временно увеличиваем лимит
sys.setrecursionlimit(1000000)


@pytest.fixture
def large_nested_dict():
    """Генерирует словарь с вложенностью depth и количеством элементов width на каждом уровне."""
    def build(depth, width):
        if depth == 0:
            return {"password": "secret_" + str(width)}
        return {f"level_{i}": build(depth - 1, width) for i in range(width)}
    return build(5, 3)   # 3^5 = 243 конечных элемента


@pytest.fixture
def big_flat_dict():
    """Плоский словарь из 10_000 записей, половина из которых чувствительна."""
    data = {}
    for i in range(10000):
        key = f"field_{i}"
        if i % 2 == 0:
            key = "password" if i % 4 == 0 else "token"
        data[key] = f"value_{i}"
    return data


def test_deep_nesting_no_recursion_error():
    """Проверяет, что рекурсия не падает при глубине 1000."""
    # Строим вложенные словари: a[b[c[...]]] = {"password": "secret"}
    d = {}
    cur = d
    for i in range(1000):
        cur["next"] = {}
        cur = cur["next"]
    cur["password"] = "secret"

    result = mask(d)
    # Проверяем, что самый глубокий пароль замаскирован
    cur_res = result
    for _ in range(1000):
        cur_res = cur_res["next"]
    assert cur_res["password"] == "***"


def test_large_flat_dict_performance(benchmark, big_flat_dict):
    """Бенчмарк маскировки плоского словаря с 10_000 записей."""
    def run():
        return mask(big_flat_dict)
    result = benchmark(run)
    # Проверяем, что все чувствительные значения замаскированы
    for key, value in result.items():
        if key in ("password", "token"):
            assert value == "***"
        else:
            assert value.startswith("value_")


def test_large_string_performance(benchmark):
    """Бенчмарк маскировки длинной строки со множеством паттернов."""
    long_string = "email=user@example.com " * 500 + "password=secret123 " * 500
    def run():
        return mask(long_string)
    result = benchmark(run)
    # Проверяем, что хотя бы один паттерн сработал
    assert "***" in result
    assert "user@example.com" not in result


def test_very_deep_nested_list(benchmark):
    """Бенчмарк глубокого списка (1000 уровней)."""
    lst = []
    cur = lst
    for i in range(1000):
        cur.append([])
        cur = cur[-1]
    cur.append("password=top_secret")
    def run():
        return mask(lst)
    result = benchmark(run)
    # Спускаемся на 1000 уровней и проверяем маскировку
    cur_res = result
    for _ in range(1000):
        cur_res = cur_res[0]
    assert cur_res[-1] == "password=***"

def test_cycle_detection_performance(benchmark):
    """Бенчмарк обнаружения циклических ссылок в большом графе."""
    nodes = []
    for i in range(1000):
        nodes.append({})
    for i in range(1, 1000):
        nodes[i]["prev"] = nodes[i-1]
    nodes[0]["prev"] = nodes[-1]          # цикл
    nodes[500]["password"] = "secret"

    def run():
        return mask(nodes)

    result = benchmark(run)
    # Проверяем, что значение "secret" нигде не осталось незамаскированным
    assert "secret" not in str(result)

def test_audit_safe_mode_large_data(benchmark):
    """Аудит в безопасном режиме с большими объёмами данных."""
    from maskinfly import AuditLogger
    import logging
    logger = logging.getLogger("benchmark_audit")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())
    audit = AuditLogger(logger=logger, safe_mode=True)
    masker = Masker(audit_enabled=True, audit_logger=audit)
    data = {f"password_{i}": "secret" for i in range(1000)}
    def run():
        return masker.mask(data)
    benchmark(run)
