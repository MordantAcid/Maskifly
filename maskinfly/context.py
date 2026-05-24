import threading
from contextlib import contextmanager

# thread-local storage для флага отключения маскировки
_local = threading.local()

def _is_masking_disabled() -> bool:
    """Возвращает True, если маскировка отключена для текущего потока."""
    return getattr(_local, 'disabled', False)

def _set_masking_disabled(disabled: bool) -> None:
    """Устанавливает флаг отключения маскировки для текущего потока."""
    _local.disabled = disabled

@contextmanager
def disabled():
    """
    Контекстный менеджер, временно отключающий маскировку.
    Внутри блока with маскировка не применяется.
    Поддерживает вложенные вызовы и корректно работает в многопоточном окружении.
    """
    previous = _is_masking_disabled()
    _set_masking_disabled(True)
    try:
        yield
    finally:
        _set_masking_disabled(previous)
