# maskinfly

**maskinfly** – это универсальная библиотека для Python, объединяющая:
- **Рекурсивную маскировку** чувствительных данных (пароли, токены, email, номера карт, SSN, IP и др.)
- **Лёгкий autograd** и базовые компоненты для создания нейронных сетей (тензоры с автоматическим дифференцированием, слои, оптимизаторы).

## Возможности

### Маскировка данных

- Рекурсивная обработка `dict`, `list`, `str`, `pydantic.SecretStr`.
- Встроенные регулярные выражения: пароли, JWT, email, кредитные карты (шаблон), SSN, IP-адреса, токены.
- Маскировка по имени переменной (например, `password = "secret"` → `***`).
- Аудит замен: логирование пути, причины и типа замаскированного значения.
- Простой интерфейс: функция `mask()` или класс `Masker`.

###  Autograd и нейронные сети

- **`Tensor`** – многомерный массив (обёртка над `numpy`) с поддержкой autograd.
- **Автоматическое дифференцирование** – градиенты скалярных функций через `.backward()`.
- **Базовые слои**: `Linear`, `ReLU`, `Sequential`.
- **Функции потерь**: `mse_loss`.
- **Оптимизатор**: `SGD`.
- **Контекстный менеджер `no_grad()`** для отключения вычисления градиентов.

## Установка

```bash
pip install maskify

git clone https://github.com/MordantAcid/maskifly.git

Для поддержки pydantic.SecretStr установите дополнительную зависимость:

pip install .[pydantic]

Быстрый старт

Маскировка данных

from maskinfly import mask

# Словарь с конфиденциальными полями
data = {
    "user": "alice",
    "password": "secret123",
    "token": "abc123xyz",
    "email": "alice@example.com"
}
masked = mask(data)
print(masked)
# {'user': 'alice', 'password': '***', 'token': '***', 'email': 'alice@example.com'}

# Строка с JWT
jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
print(mask(f"Authorization: {jwt}"))
# 'Authorization: ***'

# Включение аудита (логи в stderr)
mask(data, audit_enabled=True)

Использование класса Masker с собственным логгером

from maskinfly import Masker, AuditLogger
import logging

custom_logger = logging.getLogger("my_audit")
audit = AuditLogger(logger=custom_logger)
masker = Masker(audit_enabled=True, audit_logger=audit)

masker.mask({"api_key": "ABCD1234"})

Работа с тензорами и autograd

from maskinfly import Tensor, no_grad

# Создание тензоров
a = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
b = Tensor([[5.0, 6.0], [7.0, 8.0]], requires_grad=True)

# Операции
c = a.matmul(b)          # матричное умножение
loss = c.sum()           # скалярная потеря
loss.backward()          # вычисление градиентов

print(a.grad)            # градиент по a
print(b.grad)            # градиент по b

# Отключение градиентов
with no_grad():
    d = a + b            # здесь градиенты не вычисляются

Простая нейронная сеть

from maskinfly import nn, optim
from maskinfly.tensor import Tensor

# Данные (XOR)
X = Tensor([[0, 0], [0, 1], [1, 0], [1, 1]], requires_grad=False)
y = Tensor([[0], [1], [1], [0]], requires_grad=False)

# Модель
model = nn.Sequential(
    nn.Linear(2, 4),
    nn.ReLU(),
    nn.Linear(4, 1)
)

optimizer = optim.SGD(model.parameters(), lr=0.1)

# Обучение
for epoch in range(1000):
    pred = model(X)
    loss = nn.mse_loss(pred, y)
    
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()
    
    if epoch % 200 == 0:
        print(f"Epoch {epoch}, loss: {loss.data.item():.4f}")

# Проверка
print(model(X).data)

Лицензия
MIT. Подробнее в файле LICENSE.
