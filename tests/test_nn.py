import numpy as np
import pytest
from maskinfly.tensor import Tensor
from maskinfly.nn import Module, Linear, ReLU, Sequential, mse_loss
from maskinfly.optim import SGD

def test_linear_forward():
    layer = Linear(3, 2)
    x = Tensor(np.random.randn(1, 3))
    out = layer(x)
    assert out.shape == (1, 2)
    assert len(layer.parameters()) == (2 if layer.b is not None else 1)

def test_linear_parameters():
    layer = Linear(4, 5, bias=False)
    params = layer.parameters()
    assert len(params) == 1
    assert params[0] is layer.W

def test_linear_backward():
    layer = Linear(2, 2)
    x = Tensor([[1.0, 2.0]], requires_grad=True)
    out = layer(x)
    loss = out.sum()
    loss.backward()
    # Проверяем, что градиенты на параметрах и x не None
    assert layer.W.grad is not None
    if layer.b is not None:
        assert layer.b.grad is not None
    assert x.grad is not None

def test_relu_forward():
    relu = ReLU()
    x = Tensor([-1, 0, 2], requires_grad=True)
    out = relu(x)
    np.testing.assert_array_equal(out.data, [0, 0, 2])

def test_sequential():
    model = Sequential(
        Linear(2, 3),
        ReLU(),
        Linear(3, 1)
    )
    x = Tensor([[1.0, 2.0]])
    out = model(x)
    assert out.shape == (1, 1)
    # проверка количества параметров
    total_params = 0
    for p in model.parameters():
        total_params += p.data.size
    # Linear1: 2*3 + 3 = 9, Linear2: 3*1 + 1 = 4, всего 13
    assert total_params == 13

def test_mse_loss():
    pred = Tensor([1.0, 2.0, 3.0], requires_grad=True)
    target = Tensor([1.5, 2.5, 3.5])
    loss = mse_loss(pred, target)
    loss.backward()
    # производная: (pred-target)*2/n, n=3
    expected_grad = (pred.data - target.data) * 2 / 3
    assert pred.grad is not None
    np.testing.assert_array_almost_equal(pred.grad, expected_grad)

def test_module_zero_grad():
    linear = Linear(2, 2)
    # совершаем forward и backward
    x = Tensor([[1.0, 2.0]])
    out = linear(x)
    out.sum().backward()
    assert linear.W.grad is not None
    linear.zero_grad()
    assert np.all(linear.W.grad == 0)
    if linear.b is not None:
        assert np.all(linear.b.grad == 0)

def test_sequential_and_optimizer_integration():
    model = Sequential(Linear(1, 4), ReLU(), Linear(4, 1))
    optim = SGD(model.parameters(), lr=0.1)
    x = Tensor([[2.0]])
    target = Tensor([[10.0]])
    pred = model(x)
    loss = mse_loss(pred, target)
    loss.backward()
    # сохраним копии весов до шага
    old_params = [p.data.copy() for p in model.parameters()]
    optim.step()
    for p, old in zip(model.parameters(), old_params):
        if p.requires_grad:
            assert not np.allclose(p.data, old)  # веса должны измениться
