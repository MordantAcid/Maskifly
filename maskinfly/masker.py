import re
from typing import Any, Dict, List, Tuple, Optional, Union
from collections.abc import Mapping, Sequence
from maskinfly.patterns import PATTERNS, DEFAULT_MASK
from maskinfly.audit import AuditLogger
from maskinfly.utils import find_variable_name, SENSITIVE_VAR_NAMES

try:
    from pydantic import SecretStr
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    SecretStr = None

class Masker:
    def __init__(self, audit_enabled: bool = False, audit_logger: Optional[AuditLogger] = None):
        self.audit_enabled = audit_enabled
        self.audit = audit_logger or AuditLogger() if audit_enabled else None
        self.patterns = PATTERNS.copy()
        self.mask_str = DEFAULT_MASK

    def mask(self, data: Any, path: str = "") -> Any:
        if data is None:
            return None

        # Маскировка по типу SecretStr
        if HAS_PYDANTIC and SecretStr is not None and isinstance(data, SecretStr):
            if self.audit_enabled and self.audit:
                self.audit.log(path or "root", "type", "SecretStr")
            return self.mask_str

        # Маскировка строк
        if isinstance(data, str):
            return self.mask_string(data, path)

        # Маскировка словарей
        if isinstance(data, Mapping):
            new_dict = {}
            for key, val in data.items():
                new_path = f"{path}.{key}" if path else key
                # Если ключ чувствительный, маскируем значение независимо от его типа
                if key.lower() in SENSITIVE_VAR_NAMES:
                    # Маскируем только если это строка или SecretStr
                    if isinstance(val, str):
                        masked_val = self.mask_str
                        if self.audit_enabled and self.audit:
                            self.audit.log(new_path, "varname", "str")
                    elif HAS_PYDANTIC and SecretStr is not None and isinstance(val, SecretStr):
                        masked_val = self.mask_str
                        if self.audit_enabled and self.audit:
                            self.audit.log(new_path, "varname", "SecretStr")
                    else:
                        # Для нестроковых значений просто рекурсивно маскируем
                        masked_val = self.mask(val, new_path)
                    new_dict[key] = masked_val
                else:
                    new_dict[key] = self.mask(val, new_path)
            return new_dict

        # Маскировка последовательностей (кроме строк)
        if isinstance(data, Sequence) and not isinstance(data, (str, bytes)):
            return [self.mask(item, f"{path}[i]") for i, item in enumerate(data)]

        # Остальные типы не маскируем
        return data

    def mask_string(self, value: str, path: str) -> str:
        masked = value
        reason = None

        # 1. Паттерны
        for pattern_name, regex in self.patterns.items():
            if regex.search(masked):
                masked = regex.sub(self._replacer, masked)
                reason = "pattern"
                break

        # 2. По имени переменной (если еще не замаскировано)
        if reason is None:
            var_name = find_variable_name(value, frame_depth=3)
            if var_name and var_name.lower() in SENSITIVE_VAR_NAMES:
                masked = self.mask_str
                reason = "varname"

        # Аудит
        if self.audit_enabled and reason and masked != value and self.audit:
            self.audit.log(path, reason, "str")

        return masked

    @staticmethod
    def _replacer(match: re.Match) -> str:
        groups = match.groups()
        if groups:
            last_group = groups[-1]
            return match.string[:match.start(len(groups))] + DEFAULT_MASK + match.string[match.end():]
        return DEFAULT_MASK