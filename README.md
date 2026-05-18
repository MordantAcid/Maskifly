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
- **Поддержка `pydantic.SecretStr`** (опционально).
- **Кастомизация** маскирующей строки и добавление своих regex-паттернов.

###  Autograd и нейронные сети

- **`Tensor`** – многомерный массив (обёртка над `numpy`) с поддержкой autograd.
- **Автоматическое дифференцирование** – градиенты скалярных функций через `.backward()`.
- **Базовые слои**: `Linear`, `ReLU`, `Sequential`.
- **Функции потерь**: `mse_loss`.
- **Оптимизатор**: `SGD`.
- **Контекстный менеджер `no_grad()`** для отключения вычисления градиентов.
- **Расширенные операции**: `exp`, `log`, `mean`, `stack` и работа с broadcasting.

## Установка

```bash
pip install maskinfly

Для поддержки pydantic.SecretStr установите дополнительную зависимость:

pip install maskinfly[pydantic]

Либо клонируйте репозиторий:

git clone https://github.com/MordantAcid/maskinfly.git

cd maskinfly

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

Маскировка по имени переменной
Библиотека может автоматически определять имя переменной и маскировать значение, если оно совпадает с чувствительным списком (password, token, api_key и т.д.).

from maskinfly import mask

# Включите auto_varname
secret = "my_secret_pass"
result = mask(secret, auto_varname=True)
print(result)  # '***'

⚠️ Внимание: Функция find_variable_name, используемая при auto_varname=True, работает через интроспекцию стека и не рекомендуется для использования в production из-за низкой производительности. Для production-сценариев лучше передавать имя переменной явно через параметр var_name.

# Явное указание имени переменной (быстрее и надёжнее)
result = mask("my_secret_pass", var_name="password")

Работа с pydantic.SecretStr

from pydantic import SecretStr
from maskinfly import mask

secret = SecretStr("very_secret")
masked = mask(secret)
print(masked)  # '***'

Кастомизация маскировки

from maskinfly import Masker

# Изменение маскирующей строки
masker = Masker()
masker.mask_str = "[MASKED]"
print(masker.mask("password=12345"))  # 'password=[MASKED]'

# Добавление своего паттерна
import re
masker.patterns["my_pattern"] = re.compile(r"my_secret=\S+")
print(masker.mask("my_secret=abc123"))  # 'my_secret=***'

Использование AuditLogger для аудита

from maskinfly import AuditLogger, Masker

audit = AuditLogger()  # логирует в stderr
masker = Masker(audit_enabled=True, audit_logger=audit)
masker.mask({"api_key": "ABCD1234"})
# В stderr: 2025-... - MASKIFY_AUDIT - Значение маски 'api_key' | reason=varname | type=str

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

# Пример с broadcasting и нелинейностями
x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x ** 2).relu().exp()
y.mean().backward()
print(x.grad)

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
