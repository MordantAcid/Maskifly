import re
from typing import Any, Dict, List, Tuple, Optional, Union, Callable
from collections.abc import Mapping, Sequence
from maskinfly.patterns import PATTERNS, DEFAULT_MASK_CHAR, DEFAULT_MASK_LENGTH, full_mask_replacer
from maskinfly.audit import AuditLogger
from maskinfly.utils import find_variable_name, SENSITIVE_VAR_NAMES

try:
    from pydantic import SecretStr
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    SecretStr = None

class Masker:
    def __init__(self,
                 audit_enabled: bool = False,
                 audit_logger: Optional[AuditLogger] = None,
                 auto_varname: bool = False,
                 mask_char: str = DEFAULT_MASK_CHAR,
                 mask_length: int = DEFAULT_MASK_LENGTH,
                 custom_patterns: Optional[Dict[str, Tuple[re.Pattern, Callable]]] = None):
        """
        :param audit_enabled: включить аудит
        :param audit_logger: логгер для аудита
        :param auto_varname: автоматически определять имя переменной (медленно)
        :param mask_char: символ маски
        :param mask_length: длина маски
        :param custom_patterns: дополнительные паттерны (переопределяют встроенные)
        """
        self.audit_enabled = audit_enabled
        self.audit = audit_logger or AuditLogger() if audit_enabled else None
        self.auto_varname = auto_varname
        self.mask_char = mask_char
        self.mask_length = mask_length

        # Объединяем встроенные и пользовательские паттерны (пользовательские приоритетнее)
        self.patterns = PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def _get_mask_str(self) -> str:
        """Возвращает строку-маску заданной длины."""
        return self.mask_char * self.mask_length

    def _apply_pattern(self, value: str) -> Tuple[str, Optional[str]]:
        """
        Применяет первый подходящий паттерн к строке.
        Возвращает (замаскированная_строка, имя_паттерна_или_None).
        """
        for pattern_name, (regex, replace_func) in self.patterns.items():
            if regex.search(value):
                # Заменяем все вхождения паттерна в строке
                masked = regex.sub(lambda m: replace_func(m, self.mask_char, self.mask_length), value)
                return masked, pattern_name
        return value, None

    def mask(self, data: Any, path: str = "", var_name: Optional[str] = None) -> Any:
        if data is None:
            return None

        # Маскировка SecretStr
        if HAS_PYDANTIC and SecretStr is not None and isinstance(data, SecretStr):
            if self.audit_enabled and self.audit:
                self.audit.log(path or "root", "type", "SecretStr")
            return self._get_mask_str()

        # Маскировка строк
        if isinstance(data, str):
            return self.mask_string(data, path, var_name=var_name)

        # Рекурсивная обработка словарей
        if isinstance(data, Mapping):
            new_dict = {}
            for key, val in data.items():
                new_path = f"{path}.{key}" if path else key
                # Чувствительный ключ -> маскируем значение
                if key.lower() in SENSITIVE_VAR_NAMES:
                    if isinstance(val, str):
                        masked_val = self._get_mask_str()
                        if self.audit_enabled and self.audit:
                            self.audit.log(new_path, "varname", "str")
                    elif HAS_PYDANTIC and SecretStr is not None and isinstance(val, SecretStr):
                        masked_val = self._get_mask_str()
                        if self.audit_enabled and self.audit:
                            self.audit.log(new_path, "varname", "SecretStr")
                    else:
                        masked_val = self.mask(val, new_path)
                    new_dict[key] = masked_val
                else:
                    new_dict[key] = self.mask(val, new_path)
            return new_dict

        # Рекурсивная обработка последовательностей
        if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
            return [self.mask(item, f"{path}[i]") for i, item in enumerate(data)]

        return data

    def mask_string(self, value: str, path: str, var_name: Optional[str] = None) -> str:
        masked = value
        reason = None

        # 1. Применяем паттерны
        masked, pattern_name = self._apply_pattern(value)
        if masked != value:
            reason = f"pattern:{pattern_name}" if pattern_name else "pattern"

        # 2. Маскировка по имени переменной (если ещё не замаскировано)
        if reason is None:
            if var_name is not None:
                name = var_name
            elif self.auto_varname:
                name = find_variable_name(value, frame_depth=3)
            else:
                name = None

            if name and name.lower() in SENSITIVE_VAR_NAMES:
                masked = self._get_mask_str()
                reason = "varname"

        # Аудит
        if self.audit_enabled and reason and masked != value and self.audit:
            self.audit.log(path, reason, "str")

        return masked
