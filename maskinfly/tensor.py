from __future__ import annotations
import numpy as np
from typing import Any, List, Optional, Callable, Union
from maskinfly.autograd import Context, no_grad

class Tensor:
    """Тензор с поддержкой автоматического дифференцирования."""
    
    def __init__(self, data: Any, requires_grad: bool = False, _children: tuple = ()):
        # Поддержка различных входных типов, включая скалярные numpy-типы
        if isinstance(data, (int, float)):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, list):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, tuple):
            data = np.array(data, dtype=np.float32)
        elif isinstance(data, (np.integer, np.floating)):
            # np.int32, np.float64 и т.д. -> скалярный массив размерности 0
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
            # Поддержка скаляров (форма ()) и тензоров с одним элементом
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
    
    # ---------- операторы с autograd ----------
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
        if requires_grad:
            result._ctx = Context(_stack_backward, None)
        return result


# ----- функции операций (регистрируют граф) -----
def _reduce_grad(grad: np.ndarray, original_shape: tuple) -> np.ndarray:
    """Приводит градиент к форме original_shape с учётом broadcasting."""
    if grad.shape == original_shape:
        return grad

    # Если у градиента больше измерений, суммируем по первым лишним осям
    if grad.ndim > len(original_shape):
        axes = tuple(range(grad.ndim - len(original_shape)))
        grad = grad.sum(axis=axes)

    # Если после суммирования измерений меньше, добавляем оси слева (размер 1)
    if grad.ndim < len(original_shape):
        grad = grad.reshape((1,) * (len(original_shape) - grad.ndim) + grad.shape)

    return grad

def _add(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    if not isinstance(a, Tensor):
        a = Tensor(a, requires_grad=False)
    if not isinstance(b, Tensor):
        b = Tensor(b, requires_grad=False)
    
    data = a.data + b.data
    requires_grad = a.requires_grad or b.requires_grad
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))
    
    def _add_backward(ctx, grad):
        grad_a = None
        if a.requires_grad:
            grad_a = _reduce_grad(grad, a.data.shape)
        grad_b = None
        if b.requires_grad:
            grad_b = _reduce_grad(grad, b.data.shape)
        return grad_a, grad_b
    
    if requires_grad:
        result._ctx = Context(_add_backward, None)
    return result

def _mul(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    if not isinstance(a, Tensor):
        a = Tensor(a, requires_grad=False)
    if not isinstance(b, Tensor):
        b = Tensor(b, requires_grad=False)
    
    data = a.data * b.data
    requires_grad = a.requires_grad or b.requires_grad
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))
    
    def _mul_backward(ctx, grad):
        grad_a = (grad * b.data) if a.requires_grad else None
        grad_b = (grad * a.data) if b.requires_grad else None
        return grad_a, grad_b
    
    if requires_grad:
        result._ctx = Context(_mul_backward, None)
    return result


def _neg(a: Tensor) -> Tensor:
    result = Tensor(-a.data, requires_grad=a.requires_grad, _children=(a,))
    def _neg_backward(ctx, grad): return -grad
    if a.requires_grad:
        result._ctx = Context(_neg_backward, None)
    return result


def _div(a: Union[Tensor, float, int], b: Union[Tensor, float, int]) -> Tensor:
    return a * (b ** -1.0)


def _pow(a: Tensor, power: float) -> Tensor:
    data = a.data ** power
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _pow_backward(ctx, grad):
        return grad * power * (a.data ** (power - 1))
    if a.requires_grad:
        result._ctx = Context(_pow_backward, None)
    return result


def _matmul(a: Tensor, b: Tensor) -> Tensor:
    data = a.data @ b.data
    requires_grad = a.requires_grad or b.requires_grad
    result = Tensor(data, requires_grad=requires_grad, _children=(a, b))
    def _matmul_backward(ctx, grad):
        grad_a = grad @ b.data.T if a.requires_grad else None
        grad_b = a.data.T @ grad if b.requires_grad else None
        return grad_a, grad_b
    if requires_grad:
        result._ctx = Context(_matmul_backward, None)
    return result


def _sum(a: Tensor, axis: Optional[int] = None) -> Tensor:
    data = a.data.sum(axis=axis)
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _sum_backward(ctx, grad):
        shape = a.shape
        if axis is None:
            grad = np.full(shape, grad.item())
        else:
            grad = np.expand_dims(grad, axis=axis)
            grad = np.broadcast_to(grad, shape)
        return grad
    if a.requires_grad:
        result._ctx = Context(_sum_backward, None)
    return result


def _reshape(a: Tensor, shape: tuple) -> Tensor:
    data = a.data.reshape(shape)
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _reshape_backward(ctx, grad):
        return grad.reshape(a.shape)
    if a.requires_grad:
        result._ctx = Context(_reshape_backward, None)
    return result


def _relu(a: Tensor) -> Tensor:
    data = np.maximum(0, a.data)
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _relu_backward(ctx, grad):
        return grad * (a.data > 0)
    if a.requires_grad:
        result._ctx = Context(_relu_backward, None)
    return result


def _exp(a: Tensor) -> Tensor:
    data = np.exp(a.data)
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _exp_backward(ctx, grad):
        return grad * result.data
    if a.requires_grad:
        result._ctx = Context(_exp_backward, None)
    return result


def _log(a: Tensor) -> Tensor:
    data = np.log(a.data + 1e-8)  # стабильность
    result = Tensor(data, requires_grad=a.requires_grad, _children=(a,))
    def _log_backward(ctx, grad):
        return grad / (a.data + 1e-8)
    if a.requires_grad:
        result._ctx = Context(_log_backward, None)
    return result
