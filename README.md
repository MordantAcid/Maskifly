skinfly версии 0.2.0.

markdown
# maskinfly

**maskinfly** – универсальная библиотека для Python, объединяющая:
- **Рекурсивную маскировку** чувствительных данных (пароли, токены, email, номера карт, SSN, IP и др.)
- **Лёгкий autograd** и базовые компоненты для создания нейронных сетей (тензоры с автоматическим дифференцированием, слои, оптимизаторы).
- **CLI-утилиту** для быстрой маскировки и проверки файлов JSON/YAML.

## Содержание

- [Возможности](#возможности)
- [Установка](#установка)
- [Быстрый старт](#быстрый-старт)
  - [Маскировка данных](#маскировка-данных)
  - [Autograd и нейронные сети](#autograd-и-нейронные-сети)
- [Расширенное использование](#расширенное-использование)
  - [Параметры функции `mask()`](#параметры-функции-mask)
  - [Глубокое маскирование (`deep_mask`)](#глубокое-маскирование-deep_mask)
  - [Добавление собственных паттернов](#добавление-собственных-паттернов)
  - [Загрузка конфигурации из JSON/YAML](#загрузка-конфигурации-из-jsonyaml)
  - [Аудит с JSON и кастомным обработчиком](#аудит-с-json-и-кастомным-обработчиком)
  - [Обработка циклических ссылок](#обработка-циклических-ссылок)
  - [Работа с `pydantic.SecretStr`](#работа-с-pydanticsecretstr)
- [CLI утилита](#cli-утилита)
  - [Команда `mask`](#команда-mask)
  - [Команда `check`](#команда-check)
- [Декоратор `@mask_output`](#декоратор-mask_output)
- [Autograd и нейронные сети (подробно)](#autograd-и-нейронные-сети-подробно)
  - [Тензоры и операции](#тензоры-и-операции)
  - [Управление градиентами](#управление-градиентами)
  - [Построение нейронных сетей](#построение-нейронных-сетей)
- [Лицензия](#лицензия)

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
- **Добавление собственных regex-паттернов** через параметр `custom_patterns` или метод `add_pattern`.
- **Загрузка конфигурации из JSON/YAML** (классовый метод `Masker.from_config`).
- **Корректная обработка циклических ссылок** в изменяемых структурах.
- **Маскировка по чувствительным путям** (например, ключ `"password"` в словаре).
- **Управление глубиной маскировки чувствительных ключей** (`deep_mask`).

### Autograd и нейронные сети

- **`Tensor`** – многомерный массив (обёртка над `numpy`) с поддержкой autograd.
- **Автоматическое дифференцирование** – градиенты скалярных функций через `.backward()`.
- **Базовые операции**: сложение, умножение, матричное умножение, возведение в степень, ReLU, экспонента, логарифм, изменение формы, суммирование по оси, среднее, `stack`.
- **Базовые слои**: `Linear`, `ReLU`, `Sequential`.
- **Функции потерь**: `mse_loss`.
- **Оптимизатор**: `SGD`.
- **Контекстный менеджер `no_grad()`** для отключения вычисления градиентов.
- **Функция `is_grad_enabled()`** – проверка состояния вычисления градиентов.

### CLI утилита

- **`maskifly mask`** – маскировка данных в JSON/YAML файле.
- **`maskifly check`** – сканирование файла на наличие чувствительных данных без их изменения.

## Установка

'''bash

pip install maskinfly

Или из репозитария

git clone "https://github.com/MordantAcid/maskifly.git"

cd maskinfly

Для работы с YAML и Pydantic установите дополнительные зависимости:

pip install maskinfly[yaml,pydantic]

Быстрый старт
Маскировка данных

from maskinfly import mask

data = {
    "user": "alice",
    "password": "secret123",
    "token": "abc123xyz",
    "email": "alice@example.com"
}
masked = mask(data)
print(masked)
# {'user': 'alice', 'password': '***', 'token': '***', 'email': 'a***@example.com'}

По умолчанию длина маски – 3 символа, поэтому email маскируется как a***@example.com.

# Строка с JWT
jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
print(mask(f"Authorization: {jwt}"))
# 'Authorization: ***'

# Включение аудита (логи в stderr)
mask(data, audit_enabled=True)

Autograd и нейронные сети

from maskinfly import Tensor, nn, optim

# Данные (XOR)
X = Tensor([[0, 0], [0, 1], [1, 0], [1, 1]])
y = Tensor([[0], [1], [1], [0]])

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

print(model(X).data)  # приблизительно [[0], [1], [1], [0]]

Расширенное использование
Параметры функции mask()
Функция mask() поддерживает все возможности класса Masker:

mask(data,
     audit_enabled=False,
     audit_logger=None,
     auto_varname=False,
     var_name=None,
     mask_char="*",
     mask_length=3,
     custom_patterns=None,
     audit_format='text',
     audit_custom_handler=None,
     audit_app_name=None,
     deep_mask=False)

Пример с явным указанием имени переменной (рекомендуется):

result = mask("my_secret_pass", var_name="password")  # '***'

Глубокое маскирование (deep_mask)
По умолчанию, если встречается чувствительный ключ (например, "password"), всё его значение заменяется на маску.
При deep_mask=True маскировка продолжается рекурсивно внутри значения.

from maskinfly import Masker

data = {"password": {"user": "admin", "token": "secret123"}}

masker_shallow = Masker(deep_mask=False)
print(masker_shallow.mask(data))  # {'password': '***'}

masker_deep = Masker(deep_mask=True)
print(masker_deep.mask(data))     # {'password': {'user': 'admin', 'token': '***'}}

Добавление собственных паттернов
Используйте метод add_pattern для динамического добавления новых правил маскировки.

import re
from maskinfly import Masker

def my_replacer(match, mask_char, mask_length):
    return mask_char * mask_length

masker = Masker()
masker.add_pattern("my_id", r"\d{4}-\d{4}", my_replacer)
print(masker.mask("ID: 1234-5678"))  # 'ID: ***'

# Если replacer не указан, используется full_mask_replacer (полная замена)
masker.add_pattern("simple", r"\b\d{3}\b")
print(masker.mask("code 123"))  # 'code ***'

Вы можете использовать встроенные функции замены:

full_mask_replacer – полная замена на маску.

email_mask_replacer – частичная маскировка email (первый символ + маска).

key_value_mask_replacer – замена только значения после ключа.

Загрузка конфигурации из JSON/YAML
config.json

{
    "mask_char": "#",
    "mask_length": 4,
    "audit_enabled": false,
    "patterns": {
        "custom_key": {
            "regex": "(?i)(my_token)(\\s*[:=]\\s*)(\\S+)",
            "replacer": "key_value"
        }
    }
}

Использование:

from maskinfly import Masker

masker = Masker.from_config("config.json")
print(masker.mask("my_token = abc123"))  # 'my_token = ####'

Поддерживаются файлы .yaml / .yml (требуется установленный PyYAML).
Допустимые значения replacer: "full_mask", "email_mask", "key_value".

Аудит с JSON и кастомным обработчиком

from maskinfly import AuditLogger, Masker

def custom_audit_handler(entry):
    # Отправить entry в Elasticsearch, Kafka, файл и т.д.
    print(f"[CUSTOM] {entry}")

audit = AuditLogger(
    format='json',
    custom_handler=custom_audit_handler,
    app_name="my_app"
)
masker = Masker(audit_enabled=True, audit_logger=audit)
masker.mask({"api_key": "ABCD1234"})

В лог попадает JSON с полями: timestamp, path, reason, type, app_name, hash (SHA256 исходного значения).

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

CLI утилита
После установки становится доступна команда maskifly.

Команда mask
Маскирует данные в JSON/YAML файле и сохраняет результат.

maskifly mask input.json -o output.json --audit --mask-char '#' --mask-length 5

Параметры:

input – путь к входному файлу (JSON или YAML).

-o, --output – путь к выходному файлу (если не указан, вывод в stdout).

--audit – включить аудит (логи в stderr).

--config – путь к JSON/YAML конфигурации для Masker.

--mask-char – символ маски (по умолчанию *).

--mask-length – длина маски (по умолчанию 3).

--deep-mask – рекурсивно маскировать внутри чувствительных ключей.

Пример:

maskifly mask secrets.yaml --deep-mask --audit -o masked.yaml

Команда check
Сканирует файл на наличие чувствительных данных без их изменения.

maskifly check input.json --format json

Параметры:

input – путь к входному файлу.

--format – формат вывода: text (по умолчанию) или json.

Пример вывода (text):

Найдены потенциально чувствительные данные:
  - Путь: password
    Тип: key, причина: sensitive_key (пример: secret123)
  - Путь: token
    Тип: string, причина: pattern:token (пример: abc123)

Декоратор @mask_output
Автоматически маскирует возвращаемое значение функции, используя все возможности mask().

from maskinfly import mask_output

@mask_output(audit_enabled=True, mask_char='#', mask_length=5, deep_mask=True)
def get_user():
    return {"name": "Bob", "token": "xyz789", "credentials": {"password": "pass"}}

result = get_user()
# {'name': 'Bob', 'token': '#####', 'credentials': {'password': '#####'}}

Декоратор поддерживает синхронные и асинхронные функции.

Autograd и нейронные сети (подробно)
Тензоры и операции

from maskinfly import Tensor

a = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
b = Tensor([[5.0, 6.0], [7.0, 8.0]], requires_grad=True)

c = a.matmul(b)          # матричное умножение
loss = c.sum()           # скалярная потеря
loss.backward()          # вычисление градиентов

print(a.grad)            # [[5., 7.], [5., 7.]]
print(b.grad)            # [[4., 4.], [6., 6.]]

# Другие операции
x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x ** 2).relu().exp().log()
y.mean().backward()
print(x.grad)

# Объединение тензоров
t1 = Tensor([1, 2], requires_grad=True)
t2 = Tensor([3, 4], requires_grad=True)
stacked = Tensor.stack([t1, t2], axis=0)  # форма (2,2)
stacked.sum().backward()

Управление градиентами

from maskinfly.autograd import no_grad, is_grad_enabled

with no_grad():
    d = a + b            # здесь градиенты не вычисляются

print(is_grad_enabled())  # True

Построение нейронных сетей

from maskinfly import nn, optim
from maskinfly.tensor import Tensor

model = nn.Sequential(
    nn.Linear(10, 20),
    nn.ReLU(),
    nn.Linear(20, 1)
)

optimizer = optim.SGD(model.parameters(), lr=0.01)

x = Tensor(np.random.randn(32, 10))
y = Tensor(np.random.randn(32, 1))

for epoch in range(100):
    pred = model(x)
    loss = nn.mse_loss(pred, y)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

Лицензия
MIT. Подробнее в файле LICENSE.
