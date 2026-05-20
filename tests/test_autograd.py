import pytest
from maskinfly.autograd import no_grad, is_grad_enabled
from maskinfly.tensor import Tensor

def test_no_grad_context():
    assert is_grad_enabled() is True
    with no_grad():
        assert is_grad_enabled() is False
    assert is_grad_enabled() is True

def test_no_grad_disables_gradient_graph():
    a = Tensor(2.0, requires_grad=True)
    with no_grad():
        b = a + 3
    assert b.requires_grad is False, "Операция внутри no_grad не должна требовать градиентов"
    assert b._ctx is None, "Граф операций не должен строиться"

def test_no_grad_allows_creation_of_requires_grad_tensor():
    with no_grad():
        t = Tensor([1.0, 2.0], requires_grad=True)
    assert t.requires_grad is True
    assert t.grad is not None

def test_is_grad_enabled():
    assert is_grad_enabled() is True
    with no_grad():
        assert is_grad_enabled() is False
