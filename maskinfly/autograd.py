from typing import Callable, Any, Optional
from contextlib import contextmanager

class Context:
    def __init__(self, backward_fn: Callable, saved_tensors: Any):
        self.backward_fn = backward_fn
        self.saved_tensors = saved_tensors

    def backward(self, ctx, grad):
        return self.backward_fn(ctx, grad)

_global_grad_enabled = True

@contextmanager
def no_grad():
    global _global_grad_enabled
    old_state = _global_grad_enabled
    _global_grad_enabled = False
    try:
        yield
    finally:
        _global_grad_enabled = old_state

def is_grad_enabled() -> bool:
    return _global_grad_enabled
