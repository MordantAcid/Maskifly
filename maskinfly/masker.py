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
                 audit_format: str = 'text',
                 audit_custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
                 audit_app_name: Optional[str] = None,
                 deep_mask: bool = False):
        self.audit_enabled = audit_enabled
        self.auto_varname = auto_varname
        self.mask_char = mask_char
        self.mask_length = mask_length
        self.patterns = PATTERNS.copy()
        self.deep_mask = deep_mask
        if custom_patterns:
            self.patterns.update(custom_patterns)

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
        if not path:
            return False
        last_part = path.split('.')[-1] if '.' in path else path
        if last_part.startswith('[') and last_part.endswith(']'):
            return False
        bracket_pos = last_part.find('[')
        if bracket_pos != -1:
            last_part = last_part[:bracket_pos]
        return last_part.lower() in SENSITIVE_VAR_NAMES

    def mask(self, data: Any, path: str = "", var_name: Optional[str] = None, _visited: Optional[set] = None) -> Any:
        if _visited is None:
            _visited = set()

        # Чувствительный путь
        if self._is_sensitive_path(path):
            # Для строк: при deep_mask=True не логируем сейчас – это сделает mask_string
            if isinstance(data, str):
                if not self.deep_mask:
                    if self.audit_enabled and self.audit:
                        self.audit.log(path, "sensitive_path", type(data).__name__, value=data)
                    return self._get_mask_str()
                # deep_mask=True – продолжаем, не логируем
            else:
                # Нестроковые значения: логируем всегда
                if self.audit_enabled and self.audit:
                    self.audit.log(path, "sensitive_path", type(data).__name__, value=data)
                if not self.deep_mask:
                    return self._get_mask_str()
                # deep_mask=True – идём в рекурсию

        if data is None:
            return None

        # Обнаружение циклов
        if isinstance(data, (MappingABC, SequenceABC)) and not isinstance(data, str):
            obj_id = id(data)
            if obj_id in _visited:
                return self._get_mask_str()
            _visited.add(obj_id)

        # SecretStr
        if HAS_PYDANTIC and SecretStr is not None and isinstance(data, SecretStr):
            if self.audit_enabled and self.audit:
                self.audit.log(path or "root", "type", "SecretStr", value=data)
            return self._get_mask_str()

        # Строка
        if isinstance(data, str):
            return self.mask_string(data, path, var_name)

        # Словарь
        if isinstance(data, MappingABC):
            result = {}
            for key, value in data.items():
                new_path = f"{path}.{str(key)}" if path else str(key)
                result[key] = self.mask(value, new_path, var_name, _visited)
            return result

        # Последовательности
        if isinstance(data, SequenceABC) and not isinstance(data, str):
            result = []
            for i, item in enumerate(data):
                new_path = f"{path}[{i}]" if path else f"[{i}]"
                result.append(self.mask(item, new_path, var_name, _visited))
            if isinstance(data, tuple):
                return tuple(result)
            return result

        return data

    def mask_string(self, value: str, path: str, var_name: Optional[str] = None) -> str:
        # Если путь чувствительный, маскируем и логируем (для deep_mask=True аудит уже сделан в mask, но логируем ещё раз для единообразия)
        if self._is_sensitive_path(path):
            if self.audit_enabled and self.audit:
                self.audit.log(path, "sensitive_path", "str", value=value)
            return self._get_mask_str()

        masked = value
        reason = None

        masked, pattern_name = self._apply_pattern(value)
        if masked != value:
            reason = f"pattern:{pattern_name}" if pattern_name else "pattern"

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

        if self.audit_enabled and reason and masked != value and self.audit:
            self.audit.log(path, reason, "str", value=value)

        return masked
