import logging
import json
import hashlib
from datetime import datetime
from typing import Optional, Callable, Dict, Any

class AuditLogger:
    def __init__(self,
                 logger: Optional[logging.Logger] = None,
                 format: str = 'text',      # 'text' или 'json'
                 custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
                 app_name: Optional[str] = None):
        """
        Args:
            logger: логгер для вывода (если None, создаётся стандартный)
            format: формат вывода ('text' или 'json')
            custom_handler: кастомный обработчик записей (получает словарь)
            app_name: имя приложения (будет добавлено в структурированную запись)
        """
        if logger is None:
            self.logger = logging.getLogger("maskify.audit")
            if not self.logger.handlers:
                handler = logging.StreamHandler()
                formatter = logging.Formatter('%(asctime)s - MASKIFY_AUDIT - %(message)s')
                handler.setFormatter(formatter)
                self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
        else:
            self.logger = logger

        self.format = format
        self.custom_handler = custom_handler
        self.app_name = app_name

    def _hash_value(self, value: Any, max_len: int = 8) -> Optional[str]:
        """Вычисляет SHA256 хеш строкового представления значения.
        Возвращает первые max_len символов (или полный хеш, если max_len=None)."""
        if value is None:
            return None
        try:
            # Для SecretStr нужно получить реальное значение
            if hasattr(value, 'get_secret_value'):
                value = value.get_secret_value()
            # Преобразуем в строку
            str_value = str(value)
            hash_obj = hashlib.sha256(str_value.encode('utf-8'))
            full_hash = hash_obj.hexdigest()
            return full_hash[:max_len] if max_len else full_hash
        except Exception:
            return None

    def log(self,
            path: str,
            reason: str,
            value_type: str,
            value: Any = None,
            app_name: Optional[str] = None) -> None:
        """
        Логирует событие маскировки.

        Args:
            path: путь к значению (например, 'user.password')
            reason: причина маскировки ('pattern', 'varname', 'sensitive_path', 'type')
            value_type: тип значения ('str', 'SecretStr', 'int', ...)
            value: исходное значение (для вычисления хеша)
            app_name: переопределение имени приложения
        """
        # Формируем структурированную запись
        timestamp = datetime.now().isoformat()
        entry = {
            "timestamp": timestamp,
            "path": path,
            "reason": reason,
            "type": value_type,
            "app_name": app_name or self.app_name,
        }
        # Добавляем хеш, если передано значение
        if value is not None:
            entry["hash"] = self._hash_value(value)

        # Если передан кастомный обработчик, передаём ему запись
        if self.custom_handler is not None:
            self.custom_handler(entry)
            return

        # Иначе выводим в лог согласно формату
        if self.format == 'json':
            self.logger.info(json.dumps(entry))
        else:  # text format (совместимость со старым поведением)
            msg = f"Значение маски '{path}' | reason={reason} | type={value_type}"
            self.logger.info(msg)
