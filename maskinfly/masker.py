import re
import json
import yaml

from typing import Any, Dict, List, Tuple, Optional, Union, Callable, Pattern
from collections.abc import Mapping as MappingABC, Sequence as SequenceABC

from maskinfly.patterns import PATTERNS, DEFAULT_MASK_CHAR, DEFAULT_MASK_LENGTH, full_mask_replacer, email_mask_replacer, key_value_mask_replacer
from maskinfly.audit import AuditLogger
from maskinfly.utils import find_variable_name, SENSITIVE_VAR_NAMES
from maskinfly.context import _is_masking_disabled

try:
    from pydantic import SecretStr
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    SecretStr = None

# Сопоставление имён встроенных замен для конфигурации
_REPLACER_MAP = {
    "full_mask": full_mask_replacer,
    "email_mask": email_mask_replacer,
    "key_value": key_value_mask_replacer,
}

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
                 deep_mask: bool = False,
                 audit_safe_mode: bool = False):
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
                    app_name=audit_app_name,
                    safe_mode=audit_safe_mode
                )
            else:
                self.audit = audit_logger
                if audit_safe_mode and not getattr(audit_logger, 'safe_mode', False):
                    import warnings
                    warnings.warn(
                        "audit_safe_mode=True, но передан внешний AuditLogger без safe_mode. "
                        "Безопасный режим не применяется.",
                        UserWarning
                    )
        else:
            self.audit = None

    def add_pattern(self, name: str, regex: Union[str, re.Pattern],
                    replacer: Optional[Callable[[re.Match, str, int], str]] = None) -> None:
        """
        Добавляет новый паттерн маскировки в экземпляр Masker.

        Args:
            name: Уникальное имя паттерна.
            regex: Регулярное выражение (строка или скомпилированный re.Pattern).
            replacer: Функция замены, принимающая (match, mask_char, mask_length).
                      Если None, используется full_mask_replacer.
        """
        if isinstance(regex, str):
            regex = re.compile(regex)
        if replacer is None:
            replacer = full_mask_replacer
        self.patterns[name] = (regex, replacer)

    @classmethod
    def from_config(cls, config_path: str, **kwargs) -> "Masker":
        """
        Создаёт Masker из JSON-конфигурации (опционально YAML, если установлен PyYAML).

        Пример JSON:
        {
            "mask_char": "#",
            "mask_length": 5,
            "audit_enabled": true,
            "patterns": {
                "my_id": {
                    "regex": "\\b\\d{4}-\\d{4}\\b",
                    "replacer": "full_mask"
                },
                "custom_key": {
                    "regex": "(?i)(my_token)(\\s*[:=]\\s*)(\\S+)",
                    "replacer": "key_value"
                }
            }
        }

        Допустимые replacer: "full_mask", "email_mask", "key_value".
        """
        # Попробуем загрузить YAML, если файл имеет расширение .yaml/.yml и PyYAML установлен
        if config_path.endswith(('.yaml', '.yml')):
            try:
                import yaml
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
            except ImportError:
                raise ImportError("PyYAML не установлен. Используйте JSON или установите PyYAML.")
        else:
            with open(config_path, 'r') as f:
                config = json.load(f)

        custom_patterns = {}
        for name, pat_cfg in config.get("patterns", {}).items():
            regex_str = pat_cfg["regex"]
            replacer_name = pat_cfg.get("replacer", "full_mask")
            replacer = _REPLACER_MAP.get(replacer_name)
            if replacer is None:
                raise ValueError(f"Неизвестный replacer: {replacer_name}")
            custom_patterns[name] = (re.compile(regex_str), replacer)

        # Удаляем секцию patterns, чтобы не передавать её в __init__ как обычный параметр
        config.pop("patterns", None)
        # Объединяем конфигурацию с явными kwargs (приоритет у kwargs)
        masker_kwargs = {**config, **kwargs}
        return cls(custom_patterns=custom_patterns, **masker_kwargs)

    def _get_mask_str(self) -> str:
        return self.mask_char * self.mask_length

    def _apply_pattern(self, value: str) -> Tuple[str, Optional[str]]:
        masked = value
        last_reason = None
        for pattern_name, (regex, replace_func) in self.patterns.items():
            if regex.search(masked):
                masked = regex.sub(lambda m: replace_func(m, self.mask_char, self.mask_length), masked)
                last_reason = pattern_name
        return masked, last_reason  

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

    def mask(self, data: Any, path: str = "", var_name: Optional[str] = None,
         _memo: Optional[dict] = None, _stack: Optional[set] = None) -> Any:
        """
        Рекурсивно маскирует чувствительные данные.

        :param data: входные данные (dict, list, str, число, None, SecretStr...)
        :param path: текущий путь в структуре (для аудита)
        :param var_name: явное имя переменной (приоритет над auto_varname)
        :param _memo: словарь кеша {id(obj): masked_obj} – для разделяемых объектов
        :param _stack: множество id объектов в текущем стеке вызовов – для обнаружения циклов
        :return: замаскированные данные
        """
        # Если маскировка глобально отключена для этого потока – возвращаем данные как есть
        if _is_masking_disabled():
            return data

        # Инициализация служебных структур при первом вызове
        if _memo is None:
            _memo = {}
        if _stack is None:
            _stack = set()

        obj_id = id(data)

        # Обнаружение цикла: объект уже обрабатывается в текущей ветке
        if obj_id in _stack:
            # Циклическая ссылка – возвращаем маску
            return self._get_mask_str()

        # Если объект уже был полностью обработан в другом месте – возвращаем кешированный результат
        if obj_id in _memo:
            return _memo[obj_id]

        # Чувствительный путь (для словарей и списков)
        if self._is_sensitive_path(path):
            # Для нестроковых типов: если не deep_mask, сразу возвращаем маску
            if not isinstance(data, str):
                if self.audit_enabled and self.audit:
                    self.audit.log(path, "sensitive_path", type(data).__name__, value=data)
                if not self.deep_mask:
                    return self._get_mask_str()
                # При deep_mask продолжаем обработку, но не кешируем результат? (кеширование остаётся)

        # Обработка разных типов данных
        # --- SecretStr (pydantic) ---
        if HAS_PYDANTIC and SecretStr is not None and isinstance(data, SecretStr):
            if self.audit_enabled and self.audit:
                self.audit.log(path or "root", "type", "SecretStr", value=data)
            result = self._get_mask_str()
            _memo[obj_id] = result
            return result

        # --- Строка ---
        if isinstance(data, str):
            result = self.mask_string(data, path, var_name)
            # Строки неизменяемы, кешировать их смысла нет, но можно для единообразия
            _memo[obj_id] = result
            return result

        # --- Словарь ---
        if isinstance(data, MappingABC):
            # Добавляем объект в стек, чтобы обнаружить циклы
            _stack.add(obj_id)
            result_dict = {}
            try:
                for key, value in data.items():
                    new_path = f"{path}.{str(key)}" if path else str(key)
                    result_dict[key] = self.mask(value, new_path, var_name, _memo, _stack)
            finally:
                _stack.remove(obj_id)
            _memo[obj_id] = result_dict
            return result_dict

        # --- Последовательности (list, tuple) ---
        if isinstance(data, SequenceABC) and not isinstance(data, str):
            _stack.add(obj_id)
            result_seq = []
            try:
                for i, item in enumerate(data):
                    new_path = f"{path}[{i}]" if path else f"[{i}]"
                    result_seq.append(self.mask(item, new_path, var_name, _memo, _stack))
            finally:
                _stack.remove(obj_id)
            # Сохраняем в кеш
            if isinstance(data, tuple):
                result = tuple(result_seq)
            else:
                result = result_seq
            _memo[obj_id] = result
            return result

        # --- Прочие неизменяемые типы (int, float, bool, None) ---
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
