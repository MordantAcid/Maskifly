# maskinfly

**maskinfly** – универсальная библиотека для Python, объединяющая:

- **Рекурсивную маскировку** чувствительных данных (пароли, токены, email, номера карт, SSN, IP и др.)
- **Лёгкий autograd** и базовые компоненты для создания нейронных сетей (тензоры с автоматическим дифференцированием, слои, оптимизаторы)
- **CLI-утилиту** для быстрой маскировки и проверки файлов JSON/YAML
- **Готовые интеграции** с Django и FastAPI

## Возможности

### Маскировка данных

- Рекурсивная обработка `dict`, `list`, `str`, `pydantic.SecretStr`
- Встроенные регулярные выражения: пароли, JWT, email, кредитные карты, SSN, IP-адреса, токены
- Маскировка по имени переменной (например, `password = "secret"` → `***`) или **явно через параметр `var_name`**
- **Глубокое маскирование** (`deep_mask=True`) – рекурсивная обработка значений чувствительных ключей
- **Безопасный режим аудита** – в лог попадает только временная метка и хеш (SHA256) исходного значения
- **Асинхронный неблокирующий аудит** с очередью и фоновым потоком
- Гибкий аудит: форматы `text` или `json`, кастомный обработчик, имя приложения
- Простой интерфейс: функция `mask()` или класс `Masker`
- Поддержка `pydantic.SecretStr` (опционально)
- Кастомизация маскирующего символа и длины маски
- Добавление собственных regex-паттернов через параметр `custom_patterns` или метод `add_pattern`
- Загрузка конфигурации из JSON/YAML (классовый метод `Masker.from_config`)
- Корректная обработка циклических ссылок в изменяемых структурах
- Маскировка по чувствительным путям (например, ключ `"password"` в словаре)
- **Контекстный менеджер `disabled()`** – временное отключение маскировки
- **Декоратор `@mask_output`** – автоматическая маскировка возвращаемого значения функции

### Autograd и нейронные сети

- **`Tensor`** – многомерный массив (обёртка над `numpy`) с поддержкой autograd
- **Автоматическое дифференцирование** – градиенты скалярных функций через `.backward()`
- **Базовые операции**: сложение, умножение, матричное умножение, возведение в степень, ReLU, экспонента, логарифм, изменение формы, суммирование по оси, **среднее (`mean`)**, **объединение (`stack`)**
- **Базовые слои**: `Linear`, `ReLU`, `Sequential`
- **Функции потерь**: `mse_loss`
- **Оптимизатор**: `SGD`
- **Контекстный менеджер `no_grad()`** для отключения вычисления градиентов
- **Функция `is_grad_enabled()`** – проверка состояния вычисления градиентов

### Интеграция с веб-фреймворками

- **Django**: middleware для маскировки `GET`/`POST` и JSON тела запроса
- **FastAPI**: middleware и декоратор для маскировки JSON-ответов, зависимость

### CLI утилита

- **`maskinfly mask`** – маскировка данных в JSON/YAML файле
- **`maskinfly check`** – сканирование файла на наличие чувствительных данных без их изменения (поддержка форматов вывода `text` и `json`)

## Интеграции с FastAPI:

⚠️ Важно: MaskResponseMiddleware загружает весь JSON-ответ в память для его маскировки. Для очень больших ответов (сотни мегабайт) это может привести к высокому потреблению памяти. Рекомендуется:

устанавливать разумный лимит через параметр max_size_bytes (например, max_size_bytes=10_485_760 для 10 МБ);

исключать крупные эндпоинты через exclude_paths;

для потоковой передачи данных использовать отдельные маршруты без маскировки.

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
     deep_mask=False,
     audit_safe_mode=False)

Явное указание имени переменной
Рекомендуемый способ – передать var_name, чтобы маскировать строку, даже если auto_varname=False:

result = mask("my_secret_pass", var_name="password")  # '***'

Безопасный режим аудита
Включается параметром audit_safe_mode=True. При этом в лог аудита не попадают путь, причина, тип и имя приложения – только временная метка и хеш (SHA256) исходного значения. Это полезно для соблюдения требований конфиденциальности (GDPR, PCI DSS и т.п.).

from maskinfly import mask

# В лог попадёт только {"timestamp": "...", "hash": "abcd1234"}
mask({"password": "secret"}, audit_enabled=True, audit_safe_mode=True)

Асинхронный неблокирующий аудит
Для высоконагруженных систем можно включить асинхронный режим AuditLogger. Вызов log() не блокирует основной поток, а помещает событие в очередь. Фоновый поток обрабатывает очередь и вызывает переданный асинхронный обработчик.

import asyncio
from maskinfly import AuditLogger

async def my_async_handler(entry):
    # Отправить запись в удалённую систему (Kafka, Elasticsearch, ...)
    await some_async_client.send(entry)

audit = AuditLogger(
    async_mode=True,
    async_handler=my_async_handler,
    queue_maxsize=1000   # ограничение очереди (опционально)
)

# В любом месте (синхронном или асинхронном) вызываем log() – он не блокирует
audit.log("user.password", "sensitive_key", "str", value="secret")

# При завершении приложения не забудьте остановить логгер, чтобы обработать оставшиеся записи
audit.stop(timeout=5.0)

Глубокое маскирование (deep_mask)
По умолчанию, если встречается чувствительный ключ (например, "password"), всё его значение заменяется на маску. При deep_mask=True маскировка продолжается рекурсивно внутри значения.

from maskinfly import Masker

data = {"password": {"user": "admin", "token": "secret123"}}

masker_shallow = Masker(deep_mask=False)
print(masker_shallow.mask(data))  # {'password': '***'}

masker_deep = Masker(deep_mask=True)
print(masker_deep.mask(data))     # {'password': {'user': 'admin', 'token': '***'}}

Декоратор @mask_output
Автоматически маскирует возвращаемое значение функции, используя все возможности mask(). Декоратор корректно работает как с синхронными, так и с асинхронными функциями.

from maskinfly import mask_output

@mask_output(audit_enabled=True, mask_char='#', mask_length=5, deep_mask=True)
def get_user():
    return {"name": "Bob", "token": "xyz789", "credentials": {"password": "pass"}}

result = get_user()
# {'name': 'Bob', 'token': '#####', 'credentials': {'password': '#####'}}

# Асинхронный пример
@mask_output()
async def fetch_data():
    return {"api_key": "secret"}

Контекстный менеджер disabled()
Временно отключает маскировку для текущего потока. Полезно для отладки или для вывода данных в безопасном контексте.

from maskinfly import mask, disabled

data = {"password": "secret", "user": "alice"}

print(mask(data)["password"])   # '***'

with disabled():
    print(mask(data)["password"])   # 'secret'

print(mask(data)["password"])   # снова '***'

Добавление собственных паттернов
Используйте метод add_pattern для динамического добавления новых правил маскировки. Вы можете указать свою функцию замены или использовать одну из встроенных: full_mask_replacer, email_mask_replacer, key_value_mask_replacer.

import re
from maskinfly import Masker
from maskinfly.patterns import full_mask_replacer, key_value_mask_replacer, email_mask_replacer

masker = Masker()

# Простая полная замена
masker.add_pattern("my_id", r"\d{4}-\d{4}", full_mask_replacer)
print(masker.mask("ID: 1234-5678"))  # 'ID: ***'

# Замена только значения в паре ключ=значение
masker.add_pattern("api_key", r"(?i)(api_key)(\s*[:=]\s*)(\S+)", key_value_mask_replacer)
print(masker.mask("api_key = abcd1234"))  # 'api_key = ***'

# Частичная маскировка email (локальная часть)
masker.add_pattern("my_email", r"([\w\.-]+)@([\w\.-]+\.\w+)", email_mask_replacer)
print(masker.mask("Contact: john.doe@example.com"))  # 'Contact: j***@example.com'

# Если replacer не указан, используется full_mask_replacer
masker.add_pattern("simple", r"\b\d{3}\b")
print(masker.mask("code 123"))  # 'code ***'

Загрузка конфигурации из JSON/YAML
config.json:

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

config.yaml:

mask_char: '#'
mask_length: 4
audit_enabled: false
patterns:
  custom_key:
    regex: '(?i)(my_token)(\s*[:=]\s*)(\S+)'
    replacer: key_value

Использование:

from maskinfly import Masker

masker = Masker.from_config("config.json")   # или "config.yaml"
print(masker.mask("my_token = abc123"))      # 'my_token = ####'

Аудит с JSON и кастомным обработчиком

from maskinfly import AuditLogger, Masker

def custom_audit_handler(entry):
    # Отправить entry в Elasticsearch, Kafka, файл и т.д.
    print(f"[CUSTOM] {entry}")

audit = AuditLogger(
    format='json',
    custom_handler=custom_audit_handler,
    app_name="my_app",
    safe_mode=False      # обычный режим
)
masker = Masker(audit_enabled=True, audit_logger=audit)
masker.mask({"api_key": "ABCD1234"})

В лог попадает JSON с полями: timestamp, path, reason, type, app_name, hash (SHA256 исходного значения).

Циклические ссылки
Библиотека корректно обрабатывает циклические ссылки в изменяемых структурах, заменяя повторно посещённые объекты на маску.

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

Интеграция с веб-фреймворками
Django
Добавьте MaskingMiddleware в MIDDLEWARE и настройте параметры в MASKINFLY:

# settings.py
MIDDLEWARE = [
    ...
    'maskinfly.contrib.django.MaskingMiddleware',
]

MASKINFLY = {
    'mask_char': '#',
    'mask_length': 5,
    'audit_enabled': True,
    'deep_mask': True,
}

Middleware автоматически маскирует чувствительные данные в request.GET, request.POST и в разобранном JSON теле (например, от DRF).

Вы также можете применить маскировку вручную:

from maskinfly.contrib.django import apply_mask_to_request

def my_view(request):
    apply_mask_to_request(request)   # маскирует GET/POST/JSON
    # ... остальная логика

FastAPI
Добавьте middleware для маскировки всех JSON-ответов:

from fastapi import FastAPI
from maskinfly.contrib.fastapi import setup_fastapi_masking

app = FastAPI()
setup_fastapi_masking(app, exclude_paths=["/health"])

Или используйте декоратор для конкретного обработчика:

from maskinfly.contrib.fastapi import mask_response

@app.get("/user")
@mask_response(mask_char="#", mask_length=4)
async def get_user():
    return {"name": "Alice", "password": "secret"}

Также доступна middleware-фабрика MaskResponseMiddleware и зависимость MaskResponseDependency.

CLI утилита
После установки становится доступна команда maskinfly.

Команда mask
Маскирует данные в JSON/YAML файле и сохраняет результат.

maskinfly mask input.json -o output.json --audit --mask-char '#' --mask-length 5 --deep-mask

Параметры:

input – путь к входному файлу (JSON или YAML).

-o, --output – путь к выходному файлу (если не указан, вывод в stdout).

--audit – включить аудит (логи в stderr).

--config – путь к JSON/YAML конфигурации для Masker.

--mask-char – символ маски (по умолчанию *).

--mask-length – длина маски (по умолчанию 3).

--deep-mask – рекурсивно маскировать внутри чувствительных ключей.

Пример:

maskinfly mask secrets.yaml --deep-mask --audit -o masked.yaml

Команда check
Сканирует файл на наличие чувствительных данных без их изменения.

maskinfly check input.json --format json

Параметры:

input – путь к входному файлу.

--format – формат вывода: text (по умолчанию) или json.

Пример вывода в текстовом формате:

Найдены потенциально чувствительные данные:
  - Путь: password
    Тип: key, причина: sensitive_key (пример: secret123)
  - Путь: token
    Тип: string, причина: pattern:token (пример: abc123)

В формате JSON возвращается массив объектов с полями path, type, reason, sample.

Autograd и нейронные сети (подробно)
Тензоры и операции

from maskinfly import Tensor
from maskinfly.autograd import is_grad_enabled

print(is_grad_enabled())  # True

a = Tensor([[1.0, 2.0], [3.0, 4.0]], requires_grad=True)
b = Tensor([[5.0, 6.0], [7.0, 8.0]], requires_grad=True)

c = a.matmul(b)          # матричное умножение
loss = c.sum()           # скалярная потеря
loss.backward()          # вычисление градиентов

print(a.grad)            # [[5., 7.], [5., 7.]]
print(b.grad)            # [[4., 4.], [6., 6.]]

# Дополнительные операции
x = Tensor([1.0, 2.0, 3.0], requires_grad=True)
y = (x ** 2).relu().exp().log()
y.mean().backward()      # среднее значение и обратное распространение
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
import numpy as np

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
