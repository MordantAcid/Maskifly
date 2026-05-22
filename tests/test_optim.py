import numpy as np
import pytest

from maskinfly.tensor import Tensor
from maskinfly.optim import SGD

def test_sgd_step():
    w = Tensor([1.0, 2.0], requires_grad=True)
    # создаём псевдо-градиент
    w.grad = np.array([0.1, 0.2])
    optim = SGD([w], lr=0.5)
    optim.step()
    expected = np.array([1.0 - 0.5*0.1, 2.0 - 0.5*0.2])
    np.testing.assert_array_almost_equal(w.data, expected)

def test_sgd_zero_grad():
    w = Tensor([1.0, 2.0], requires_grad=True)
    w.grad = np.array([1, 1])
    optim = SGD([w], lr=0.1)
    optim.zero_grad()
    assert np.all(w.grad == 0)

def test_sgd_with_multiple_params():
    w1 = Tensor([1.0], requires_grad=True)
    w2 = Tensor([2.0], requires_grad=True)
    w1.grad = np.array([0.5])
    w2.grad = np.array([-0.5])
    optim = SGD([w1, w2], lr=0.1)
    optim.step()
    assert w1.data == 1.0 - 0.1*0.5
    assert w2.data == 2.0 - 0.1*(-0.5)

def test_sgd_ignores_non_grad():
    w1 = Tensor([1.0], requires_grad=True)
    w2 = Tensor([2.0], requires_grad=False)
    w1.grad = np.array([0.2])
    optim = SGD([w1, w2], lr=0.1)
    optim.step()
    assert w1.data == 1.0 - 0.1*0.2
    assert w2.data == 2.0  # не изменился
