from maskinfly.tensor import Tensor
from typing import Optional, List
import numpy as np

class Module:
    def __init__(self):
        self._parameters: List[Tensor] = []
    
    def parameters(self) -> List[Tensor]:
        return self._parameters
    
    def zero_grad(self):
        for p in self.parameters():
            p.zero_grad()
    
    def forward(self, x: Tensor) -> Tensor:
        raise NotImplementedError
    
    def __call__(self, x: Tensor) -> Tensor:
        return self.forward(x)


class Linear(Module):
    def __init__(self, in_features: int, out_features: int, bias: bool = True):
        super().__init__()
        # инициализация Kaiming Uniform
        limit = np.sqrt(6 / in_features)
        W_data = np.random.uniform(-limit, limit, (in_features, out_features)).astype(np.float32)
        self.W = Tensor(W_data, requires_grad=True)
        self._parameters.append(self.W)
        if bias:
            b_data = np.zeros(out_features, dtype=np.float32)
            self.b = Tensor(b_data, requires_grad=True)
            self._parameters.append(self.b)
        else:
            self.b = None
    
    def forward(self, x: Tensor) -> Tensor:
        out = x.matmul(self.W)
        if self.b is not None:
            out = out + self.b
        return out


class ReLU(Module):
    def forward(self, x: Tensor) -> Tensor:
        return x.relu()


class Sequential(Module):
    def __init__(self, *layers: Module):
        super().__init__()
        self.layers = layers
        for layer in layers:
            self._parameters.extend(layer.parameters())
    
    def forward(self, x: Tensor) -> Tensor:
        for layer in self.layers:
            x = layer(x)
        return x


def mse_loss(pred: Tensor, target: Tensor) -> Tensor:
    diff = pred - target
    return (diff ** 2).mean()
