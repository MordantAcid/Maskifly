# maskinfly

**maskinfly** — это легковесная библиотека для рекурсивной маскировки чувствительных данных (паролей, токенов, email, номеров карт, SSN, IP-адресов и т.д.) в Python-структурах. Она автоматически обнаруживает и заменяет конфиденциальную информацию в строках, словарях и списках, а также поддерживает аудит всех произведённых замен.

## Возможности

- **Рекурсивная маскировка** — работает с вложенными словарями, списками и другими коллекциями.
- **Встроенные паттерны** — пароли, JWT, email, номера кредитных карт (регулярное выражение ошибочно, но оставлено для совместимости), SSN, IP-адреса, токены.
- **Маскировка по имени переменной** — если в коде переменная называется `password`, `api_key` и т.п., её значение будет замаскировано даже без явного паттерна.
- **Аудит** — логирование причины замены (`pattern`, `varname`, `type`) и пути к значению.
- **Поддержка `pydantic.SecretStr`** — если установлен Pydantic, объекты `SecretStr` маскируются автоматически.
- **Простой интерфейс** — функция `mask()` для быстрой маскировки или класс `Masker` для тонкой настройки.

## Установка

```bash
pip install maskify

git clone https://github.com/MordantAcid/Maskifly.git

Для поддержки pydantic.SecretStr установите дополнительную зависимость:

pip install .[pydantic]

Быстрый старт

from maskify import mask

# Маскировка в словаре
data = {
    "user": "john",
    "password": "secret123",
    "email": "john@example.com"
}
masked = mask(data)
print(masked)
# {'user': 'john', 'password': '***', 'email': 'john@example.com'}

# Маскировка в строке
text = "My token is abc123xyz"
print(mask(text))
# 'My token is ***'

# Включение аудита (лог будет выведен в stderr)
mask(data, audit_enabled=True)
# Вывод в лог: 2025-01-01 12:00:00 - MASKIFY_AUDIT - Значение маски 'password' | reason=pattern | type=str

Использование
Функция mask()
Самый простой способ — импортировать mask и передать данные:

result = mask(data, audit_enabled=False, audit_logger=None)

- data — любые данные (str, dict, list и т.д.).
- audit_enabled — если True, включает логирование аудита.
- audit_logger — собственный экземпляр AuditLogger (опционально).

Класс Masker
Для более гибкого управления создайте экземпляр Masker:

from maskify import Masker

masker = Masker(audit_enabled=True)
masked_data = masker.mask(data)

Параметры конструктора:

- audit_enabled: bool = False
- audit_logger: Optional[AuditLogger] = None

Метод mask(data, path="") принимает произвольные данные и опциональный строковый путь (используется для аудита).

Аудит: AuditLogger
По умолчанию аудит пишет в logging.getLogger("maskify.audit") с уровнем INFO и форматированием '%(asctime)s - MASKIFY_AUDIT - %(message)s'. Вы можете передать свой логгер:

import logging
from maskify import AuditLogger

custom_logger = logging.getLogger("my_audit")
audit = AuditLogger(logger=custom_logger)
masker = Masker(audit_enabled=True, audit_logger=audit)
masker.mask({"secret": "value"})

Маскировка по имени переменной
Если значение не подошло ни под один паттерн, библиотека пытается определить имя переменной, в которой оно хранится (с помощью inspect). Если имя входит в набор SENSITIVE_VAR_NAMES, значение заменяется на ***.

Чувствительные имена по умолчанию:

password, passwd, pwd, secret, token, api_key, apikey,
credit_card, creditcard, card_number, ssn, social_security,
pin, auth, bearer, private_key

Пример:

secret_token = "abc123xyz"
mask(secret_token)  # -> "***" (переменная называется secret_token)

Работа с pydantic.SecretStr
Если установлен Pydantic, объекты SecretStr маскируются вне зависимости от содержимого:

from pydantic import SecretStr
from maskify import mask

secret = SecretStr("real_password")
masked = mask(secret)  # -> "***"

Требования
Python ≥ 3.7

Для опциональной поддержки SecretStr: pydantic >= 2.0.0