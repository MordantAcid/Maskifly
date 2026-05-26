import threading
from contextlib import contextmanager
from typing import Any

class Context:
    def __init__(self, backward_fn, saved_tensors: Any):
        self.backward_fn = backward_fn
        self.saved_tensors = saved_tensors

    def backward(self, ctx, grad):
        return self.backward_fn(ctx, grad)

# Потоколокальное хранилище для флага вычисления градиентов
_thread_local = threading.local()

def _get_grad_enabled() -> bool:
    """Возвращает состояние вычисления градиентов для текущего потока (по умолчанию True)."""
    return getattr(_thread_local, 'grad_enabled', True)

def _set_grad_enabled(value: bool) -> None:
    """Устанавливает состояние вычисления градиентов для текущего потока."""
    _thread_local.grad_enabled = value

@contextmanager
def no_grad():
    """Контекстный менеджер, временно отключающий вычисление градиентов в текущем потоке."""
    old_state = _get_grad_enabled()
    _set_grad_enabled(False)
    try:
        yield
    finally:
        _set_grad_enabled(old_state)

def is_grad_enabled() -> bool:
    """Возвращает True, если вычисление градиентов включено в текущем потоке."""
    return _get_grad_enabled()
