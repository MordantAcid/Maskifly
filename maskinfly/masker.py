import re
from typing import Any, Dict, List, Tuple, Optional, Union, Callable
from collections.abc import Mapping as MappingABC, Sequence as SequenceABC
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
                 custom_patterns: Optional[Dict[str, Tuple[re.Pattern, Callable]]] = None,
                 # Новые параметры для структурированного аудита
                 audit_format: str = 'text',
                 audit_custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
                 audit_app_name: Optional[str] = None):
        self.audit_enabled = audit_enabled
        self.auto_varname = auto_varname
        self.mask_char = mask_char
        self.mask_length = mask_length
        self.patterns = PATTERNS.copy()
        if custom_patterns:
            self.patterns.update(custom_patterns)

        # Создаём AuditLogger с новыми параметрами
        if audit_enabled:
            if audit_logger is None:
                self.audit = AuditLogger(
                    format=audit_format,
                    custom_handler=audit_custom_handler,
                    app_name=audit_app_name
                )
            else:
                self.audit = audit_logger
        else:
            self.audit = None

    def _get_mask_str(self) -> str:
        return self.mask_char * self.mask_length

    def _apply_pattern(self, value: str) -> Tuple[str, Optional[str]]:
        for pattern_name, (regex, replace_func) in self.patterns.items():
            if regex.search(value):
                masked = regex.sub(lambda m: replace_func(m, self.mask_char, self.mask_length), value)
                return masked, pattern_name
        return value, None

    def _is_sensitive_path(self, path: str) -> bool:
        """Проверяет, содержит ли путь чувствительное имя (ключ словаря или имя переменной)."""
        if not path:
            return False
        # Берём последний компонент пути (после точки или просто строку)
        last_part = path.split('.')[-1] if '.' in path else path
        # Убираем индексы списков, например "[0]"
        if last_part.startswith('[') and last_part.endswith(']'):
            return False
        # Если last_part содержит '[', это комбинация "field[0]" — берём часть до '['
        bracket_pos = last_part.find('[')
        if bracket_pos != -1:
            last_part = last_part[:bracket_pos]
        return last_part.lower() in SENSITIVE_VAR_NAMES

    def mask(self, data: Any, path: str = "", var_name: Optional[str] = None, _visited: Optional[set] = None) -> Any:
        if _visited is None:
            _visited = set()

        # None не требует обработки
        if data is None:
            return None

        # Обнаружение циклических ссылок для изменяемых объектов (словари, списки, множества)
        if isinstance(data, (MappingABC, SequenceABC)) and not isinstance(data, str):
            obj_id = id(data)
            if obj_id in _visited:
                # Циклическая ссылка, возвращаем маску
                return self._get_mask_str()
            _visited.add(obj_id)

        # Маскировка SecretStr (pydantic)
        if HAS_PYDANTIC and SecretStr is not None and isinstance(data, SecretStr):
            if self.audit_enabled and self.audit:
                self.audit.log(path or "root", "type", "SecretStr", value=data)  # передаём data
            return self._get_mask_str()

        # Если путь (ключ словаря или индекс) чувствительный, маскируем значение полностью
        if self._is_sensitive_path(path):
            if self.audit_enabled and self.audit:
                self.audit.log(path, "sensitive_path", type(data).__name__, value=data)
            return self._get_mask_str()

        # Маскировка строк
        if isinstance(data, str):
            return self.mask_string(data, path, var_name)

        # Рекурсивная обработка словарей
        if isinstance(data, MappingABC):
            result = {}
            for key, value in data.items():
                new_path = f"{path}.{key}" if path else key
                result[key] = self.mask(value, new_path, var_name, _visited)
            return result

        # Рекурсивная обработка последовательностей (списки, кортежи)
        if isinstance(data, SequenceABC) and not isinstance(data, str):
            result = []
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                result.append(self.mask(item, new_path, var_name, _visited))
            if isinstance(data, tuple):
                return tuple(result)
            return result

        # Для всех остальных типов (int, float, bool, ...) возвращаем как есть
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
            self.audit.log(path, reason, "str", value=value)

        return masked
