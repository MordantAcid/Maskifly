import pytest

from maskinfly.masker import Masker

def test_cycle_in_dict():
    """Прямая циклическая ссылка: dict содержит самого себя."""
    masker = Masker()
    d = {}
    d["self"] = d
    result = masker.mask(d)
    # Цикл должен быть обнаружен, на месте ссылки – маска
    assert result["self"] == "***"
    # Остальные поля отсутствуют, но структура сохранена
    assert set(result.keys()) == {"self"}

def test_cycle_in_list():
    """Циклическая ссылка в списке."""
    masker = Masker()
    lst = []
    lst.append(lst)
    result = masker.mask(lst)
    assert len(result) == 1
    assert result[0] == "***"

def test_nested_cycle():
    """Сложный цикл: список содержит словарь, который ссылается на список."""
    masker = Masker()
    lst = []
    d = {"ref": lst}
    lst.append(d)
    result = masker.mask(lst)
    assert result[0]["ref"] == "***"      # lst уже посещён, возвращается маска
    assert len(result) == 1

def test_cycle_with_sensitive_key():
    """Циклическая ссылка внутри чувствительного поля – маскируется как обычно."""
    masker = Masker()
    inner = {}
    outer = {"password": inner}
    inner["parent"] = outer
    result = masker.mask(outer)
    # Значение по ключу "password" должно быть полностью замаскировано
    assert result["password"] == "***"

def test_no_cycle_for_primitives():
    """Простые типы не вызывают ложных циклов."""
    masker = Masker()
    data = {"a": "hello", "b": "hello"}   # одинаковые строки могут иметь один id (интернирование)
    result = masker.mask(data)
    assert result["a"] == "hello"
    assert result["b"] == "hello"

def test_cycle_audit_does_not_crash():
    """При включённом аудите цикл не должен вызывать ошибок."""
    masker = Masker(audit_enabled=True)
    d = {}
    d["cycle"] = d
    # Просто проверяем, что не падает
    result = masker.mask(d)
    assert result["cycle"] == "***"
