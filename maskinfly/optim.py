from maskinfly.tensor import Tensor
from typing import List

class SGD:
    def __init__(self, params: List[Tensor], lr: float = 0.01):
        self.params = params
        self.lr = lr
    
    def step(self):
        for p in self.params:
            if p.requires_grad and p.grad is not None:
                p.data -= self.lr * p.grad
    
    def zero_grad(self):
        for p in self.params:
            p.zero_grad()
