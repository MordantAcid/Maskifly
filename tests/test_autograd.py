import pytest
from maskinfly.autograd import no_grad, is_grad_enabled
from maskinfly.tensor import Tensor

def test_no_grad_context():
    """Проверяет, что внутри контекста no_grad флаг is_grad_enabled выключен."""
    assert is_grad_enabled() is True
    with no_grad():
        assert is_grad_enabled() is False
    assert is_grad_enabled() is True

def test_no_grad_does_not_affect_tensor_creation():
    """В текущей реализации флаг _global_grad_enabled не используется в Tensor,
    поэтому тензор с requires_grad=True всё равно создаётся с градиентами."""
    with no_grad():
        t = Tensor([1.0, 2.0], requires_grad=True)
    assert t.requires_grad is True
    assert t.grad is not None

def test_is_grad_enabled():
    assert is_grad_enabled() is True
    with no_grad():
        assert is_grad_enabled() is False
