# maskinfly

**maskinfly** – универсальная библиотека для Python, объединяющая:
- **Рекурсивную маскировку** чувствительных данных (пароли, токены, email, номера карт, SSN, IP и др.)
- **Лёгкий autograd** и базовые компоненты для создания нейронных сетей (тензоры с автоматическим дифференцированием, слои, оптимизаторы).

## Возможности

### Маскировка данных

- Рекурсивная обработка `dict`, `list`, `str`, `pydantic.SecretStr`.
- Встроенные регулярные выражения: пароли, JWT, email, кредитные карты, SSN, IP-адреса, токены.
- Маскировка по имени переменной (например, `password = "secret"` → `***`).
- **Явное указание имени переменной** через параметр `var_name` (рекомендуется для production).
- Аудит замен: логирование пути, причины, типа и **хеша** (SHA256) исходного значения.
- **Гибкий аудит**: форматы `text` или `json`, кастомный обработчик, имя приложения.
- Простой интерфейс: функция `mask()` или класс `Masker`.
- **Поддержка `pydantic.SecretStr`** (опционально).
- **Кастомизация** маскирующего символа и длины маски.
- **Добавление собственных regex-паттернов** через параметр `custom_patterns`.
- **Корректная обработка циклических ссылок** в изменяемых структурах.
- **Маскировка по чувствительным путям** (например, ключ `"password"` в словаре).

### Autograd и нейронные сети

- **`Tensor`** – многомерный массив (обёртка над `numpy`) с поддержкой autograd.
- **Автоматическое дифференцирование** – градиенты скалярных функций через `.backward()`.
- **Базовые операции**: сложение, умножение, матричное умножение, возведение в степень, релу, экспонента, логарифм, изменение формы, суммирование по оси, среднее, `stack`.
- **Базовые слои**: `Linear`, `ReLU`, `Sequential`.
- **Функции потерь**: `mse_loss`.
- **Оптимизатор**: `SGD`.
- **Контекстный менеджер `no_grad()`** для отключения вычисления градиентов.
- **Функция `is_grad_enabled()`** – проверка состояния вычисления градиентов.

## Установка

```bash
pip install maskinfly

## Установка

```bash

pip install maskinfly

Или из репозитария

git clone "https://github.com/MordantAcid/maskifly.git"

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
# {'user': 'alice', 'password': '***', 'token': '***', 'email': 'a***@example.com'}

По умолчанию длина маски – 3 символа, поэтому email маскируется как a***@example.com.# Строка с JWT
jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
print(mask(f"Authorization: {jwt}"))
# 'Authorization: ***'

# Включение аудита (логи в stderr)
mask(data, audit_enabled=True)

Настройка символа и длины маски

mask("my_secret_password", mask_char='X', mask_length=5)   # 'XXXXX'
mask("user@example.com", mask_char='*', mask_length=4)     # 'u****@example.com'

Явное указание имени переменной (рекомендуется)
Автоматическое определение имени переменной (auto_varname=True) работает через интроспекцию стека и медленно. Для production используйте параметр var_name:

result = mask("my_secret_pass", var_name="password")
print(result)  # '***'

Маскировка по имени переменной (автоматическая, не для production)

# Включите auto_varname (медленно, не рекомендуется)
secret = "my_secret_pass"
result = mask(secret, auto_varname=True)
print(result)  # '***'

Добавление своих regex-паттернов

import re
from maskinfly import mask

def my_replacer(match, mask_char, mask_length):
    return mask_char * mask_length

custom = {
    "my_id": (re.compile(r'\d{4}-\d{4}'), my_replacer)
}

data = "User ID: 1234-5678"
print(mask(data, custom_patterns=custom))  # 'User ID: ***'

Аудит с JSON и кастомным обработчиком

from maskinfly import AuditLogger, Masker

def custom_audit_handler(entry):
    # Отправить entry в Elasticsearch, Kafka и т.д.
    print(f"[CUSTOM] {entry}")

audit = AuditLogger(format='json', custom_handler=custom_audit_handler, app_name="my_app")
masker = Masker(audit_enabled=True, audit_logger=audit)
masker.mask({"api_key": "ABCD1234"})
# Вызовет custom_audit_handler со словарём, содержащим timestamp, path, reason, hash и др.

Обработка циклических ссылок
Masker корректно обрабатывает циклические ссылки, заменяя повторно встречающиеся объекты на маску:

from maskinfly import Masker

masker = Masker()
d = {}
d["self"] = d          # цикл
result = masker.mask(d)
print(result)          # {'self': '***'}

Работа с pydantic.SecretStr

from pydantic import SecretStr
from maskinfly import mask

secret = SecretStr("very_secret")
masked = mask(secret)
print(masked)  # '***'

Использование Masker с постоянными настройками

from maskinfly import Masker

masker = Masker(mask_char='#', mask_length=6)
print(masker.mask("password=12345"))  # 'password=######'

Autograd и нейронные сети
Тензоры и автоматическое дифференцирование

from maskinfly import Tensor, no_grad
from maskinfly.autograd import is_grad_enabled

# Создание тензоров
a = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
b = Tensor([[5.0, 6.0], [7.0, 8.0]], requires_grad=True)

# Операции
c = a.matmul(b)          # матричное умножение
loss = c.sum()           # скалярная потеря
loss.backward()          # вычисление градиентов

print(a.grad)            # градиент по a
print(b.grad)            # градиент по b

# Пример с broadcasting, ReLU, экспонентой, логарифмом
x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x ** 2).relu().exp().log()
y.mean().backward()
print(x.grad)

# Отключение градиентов
with no_grad():
    d = a + b            # здесь градиенты не вычисляются

# Проверка состояния
print(is_grad_enabled())  # True

Дополнительные операции тензоров

t = Tensor([[1, 2], [3, 4]], requires_grad=True)

# Суммирование по оси
s = t.sum(axis=0)
s.backward(np.array([1, 1]))

# Изменение формы
r = t.reshape(4)
r.backward(np.ones(4))

# Логарифм и экспонента
log_t = t.log()
exp_t = t.exp()

# Среднее значение
m = t.mean()
m.backward()

# Объединение тензоров
a = Tensor([1, 2], requires_grad=True)
b = Tensor([3, 4], requires_grad=True)
stacked = Tensor.stack([a, b], axis=0)
stacked.sum().backward()

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
