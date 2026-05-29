from __future__ import annotations

import numpy as np

from typing import Any, List, Optional, Callable, Union
from maskinfly.autograd import Context, no_grad, is_grad_enabled

class Tensor:
    def __init__(self, data: Any, requires_grad: bool = False, _children: tuple = ()):
        if isinstance(data, (int, float)):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, list):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, tuple):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, (np.integer, np.floating)):
            data = np.array(data, dtype=np.float32)
        elif not isinstance(data, np.ndarray):
            raise TypeError(f"Unsupported data type: {type(data)}")

        self.data = data.astype(np.float32)
        self.requires_grad = requires_grad
        self.grad: Optional[np.ndarray] = None
        self._ctx: Optional[Context] = None
        self._children: tuple = _children

        if requires_grad:
            self.grad = np.zeros_like(self.data)

    @property
    def shape(self) -> tuple:
        return self.data.shape

    def __repr__(self) -> str:
        return f"Tensor({self.data}, requires_grad={self.requires_grad})"

    def backward(self, grad: Optional[np.ndarray] = None) -> None:
        if not self.requires_grad:
            return

        if grad is None:
            if self.shape == ():
                grad = np.array(1.0, dtype=np.float32)
            elif self.data.size == 1:
                grad = np.ones_like(self.data)
            else:
                raise RuntimeError("grad must be provided for non-scalar tensors")

        if self.grad is None:
            self.grad = grad
        else:
            self.grad = self.grad + grad

        if self._ctx is not None:
            grads = self._ctx.backward(self._ctx, grad)
            if not isinstance(grads, tuple):
                grads = (grads,)
            for child, g in zip(self._children, grads):
                if child is not None and child.requires_grad and g is not None:
                    child.backward(g)

    def zero_grad(self) -> None:
        if self.grad is not None:
            self.grad = np.zeros_like(self.data)

    def numpy(self) -> np.ndarray:
        return self.data

    def __add__(self, other: Union[Tensor, float, int]) -> Tensor:
        return _add(self, other)
    def __radd__(self, other): return self + other
    def __mul__(self, other): return _mul(self, other)
    def __rmul__(self, other): return self * other
    def __neg__(self): return _neg(self)
    def __sub__(self, other): return self + (-other)
    def __rsub__(self, other): return other + (-self)
    def __truediv__(self, other): return _div(self, other)
    def __rtruediv__(self, other): return _div(other, self)
    def __pow__(self, power: float): return _pow(self, power)
    def matmul(self, other: Tensor) -> Tensor:
        return _matmul(self, other)
    def sum(self, axis: Optional[int] = None) -> Tensor:
        return _sum(self, axis)
    def reshape(self, *shape: int) -> Tensor:
        return _reshape(self, shape)
    def relu(self) -> Tensor:
        return _relu(self)
    def exp(self) -> Tensor:
        return _exp(self)
    def log(self) -> Tensor:
        return _log(self)
    def mean(self, axis: Optional[int] = None) -> Tensor:
        n = self.data.size if axis is None else self.data.shape[axis]
        return self.sum(axis) / n

    @staticmethod
    def stack(tensors: List[Tensor], axis: int = 0) -> Tensor:
        data = np.stack([t.data for t in tensors], axis=axis)
        requires_grad = any(t.requires_grad for t in tensors)
        result = Tensor(data, requires_grad=requires_grad, _children=tuple(tensors))
        def _stack_backward(ctx, grad):
            grads = [np.take(grad, i, axis=axis) for i in range(len(tensors))]
            return tuple(grads)
        if requires_grad and is_grad_enabled():
            result._ctx = Context(_stack_backward, None)
        return result

# ---------- вспомогательные функции ----------
def _reduce_grad(grad: np.ndarray, original_shape: tuple) -> np.ndarray:
    """Приводит градиент к форме original_shape, учитывая broadcasting."""
    if grad.shape == original_shape:
        return grad

    # 1. Убираем лишние ведущие оси (если grad.ndim > len(original_shape))
    extra_dims = grad.ndim - len(original_shape)
    if extra_dims > 0:
        axes = tuple(range(extra_dims))
        grad = grad.sum(axis=axes, keepdims=False)

    axes_to_sum = []
    for i, (orig_dim, grad_dim) in enumerate(zip(original_shape, grad.shape)):
        if orig_dim == 1 and grad_dim > 1:
            axes_to_sum.append(i)
    if axes_to_sum:
        grad = grad.sum(axis=tuple(axes_to_sum), keepdims=True)

    # 3. Если форма всё ещё не совпадает, выполняем reshape
    if grad.shape != original_shape:
        grad = grad.reshape(original_shape)
    return grad

def _add(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    if not isinstance(a, Tensor):
        a = Tensor(a, requires_grad=False)
    if not isinstance(b, Tensor):
        b = Tensor(b, requires_grad=False)

    data = a.data + b.data
    requires_grad = (a.requires_grad or b.requires_grad) and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))

    if requires_grad:
        def _add_backward(ctx, grad):
            grad_a = _reduce_grad(grad, a.data.shape) if a.requires_grad else None
            grad_b = _reduce_grad(grad, b.data.shape) if b.requires_grad else None
            return grad_a, grad_b
        result._ctx = Context(_add_backward, None)
    return result

def _mul(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    if not isinstance(a, Tensor):
        a = Tensor(a, requires_grad=False)
    if not isinstance(b, Tensor):
        b = Tensor(b, requires_grad=False)

    data = a.data * b.data
    requires_grad = (a.requires_grad or b.requires_grad) and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))

    if requires_grad:
        def _mul_backward(ctx, grad):
            grad_a = _reduce_grad(grad * b.data, a.data.shape) if a.requires_grad else None
            grad_b = _reduce_grad(grad * a.data, b.data.shape) if b.requires_grad else None
            return grad_a, grad_b
        result._ctx = Context(_mul_backward, None)
    return result

def _neg(a: Tensor) -> Tensor:
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(-a.data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _neg_backward(ctx, grad):
            return -grad
        result._ctx = Context(_neg_backward, None)
    return result

def _div(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    return a * (b ** -1.0)

def _pow(a: Tensor, power: float) -> Tensor:
    requires_grad = a.requires_grad and is_grad_enabled()
    data = a.data ** power
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _pow_backward(ctx, grad):
            grad_val = grad * power * (a.data ** (power - 1))
            return _reduce_grad(grad_val, a.data.shape)
        result._ctx = Context(_pow_backward, None)
    return result

def _matmul(a: Tensor, b: Tensor) -> Tensor:
    data = a.data @ b.data
    requires_grad = (a.requires_grad or b.requires_grad) and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))
    if requires_grad:
        def _matmul_backward(ctx, grad):
            grad_a = None
            grad_b = None
            if a.requires_grad:
                grad_a = grad @ b.data.T
                grad_a = _reduce_grad(grad_a, a.data.shape)
            if b.requires_grad:
                grad_b = a.data.T @ grad
                grad_b = _reduce_grad(grad_b, b.data.shape)
            return grad_a, grad_b
        result._ctx = Context(_matmul_backward, None)
    return result

def _sum(a: Tensor, axis: Optional[int] = None) -> Tensor:
    data = a.data.sum(axis=axis)
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        result._ctx = Context(_sum_backward, (a.shape, axis))
    return result

def _sum_backward(ctx, grad):
    original_shape, axis = ctx.saved_tensors
    if axis is None:
        # сумма всех элементов -> скаляр
        if grad.ndim == 0:
            grad_val = grad
        elif grad.size == 1:
            grad_val = grad.item()
        else:
            raise RuntimeError("Gradient for full sum must be scalar or have size 1")
        return np.full(original_shape, grad_val, dtype=np.float32)
    else:
        # sum по оси (одной или нескольким)
        if isinstance(axis, int):
            axes = (axis,)
        else:
            axes = tuple(axis)
        grad_expanded = grad
        for ax in sorted(axes):
            grad_expanded = np.expand_dims(grad_expanded, axis=ax)
        return np.broadcast_to(grad_expanded, original_shape)

def _reshape(a: Tensor, shape: tuple) -> Tensor:
    data = a.data.reshape(shape)
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _reshape_backward(ctx, grad):
            return grad.reshape(a.shape)
        result._ctx = Context(_reshape_backward, None)
    return result

def _relu(a: Tensor) -> Tensor:
    data = np.maximum(0, a.data)
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _relu_backward(ctx, grad):
            grad_val = grad * (a.data > 0)
            return _reduce_grad(grad_val, a.data.shape)
        result._ctx = Context(_relu_backward, None)
    return result

def _exp(a: Tensor) -> Tensor:
    data = np.exp(a.data)
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _exp_backward(ctx, grad):
            grad_val = grad * result.data
            return _reduce_grad(grad_val, a.data.shape)
        result._ctx = Context(_exp_backward, None)
    return result

def _log(a: Tensor) -> Tensor:
    data = np.log(a.data + 1e-8)
    requires_grad = a.requires_grad and is_grad_enabled()
    result = Tensor(data, requires_grad=requires_grad, _children=(a,))
    if requires_grad:
        def _log_backward(ctx, grad):
            grad_val = grad / (a.data + 1e-8)
            return _reduce_grad(grad_val, a.data.shape)
        result._ctx = Context(_log_backward, None)
    return result
