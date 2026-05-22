import logging
import json
import hashlib

from datetime import datetime
from typing import Optional, Callable, Dict, Any

try:
    from pydantic import SecretStr
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    SecretStr = None

class AuditLogger:
    def __init__(self,
                 logger: Optional[logging.Logger] = None,
                 format: str = 'text',
                 custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
                 app_name: Optional[str] = None,
                 safe_mode: bool = False):          # новый параметр
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
        self.safe_mode = safe_mode

    def _hash_value(self, value: Any, max_len: int = 8) -> Optional[str]:
        if value is None:
            return None
        try:
            if HAS_PYDANTIC and SecretStr is not None and isinstance(value, SecretStr):
                value = value.get_secret_value()
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
        timestamp = datetime.now().isoformat()

        # Безопасный режим: только хеш и метка времени
        if self.safe_mode:
            entry = {
                "timestamp": timestamp,
                "hash": self._hash_value(value),
            }
            # Для текстового формата тоже выводим минимум
            if self.custom_handler is not None:
                self.custom_handler(entry)
                return

            if self.format == 'json':
                self.logger.info(json.dumps(entry))
            else:
                msg = f"MASKING EVENT hash={entry['hash']}"
                self.logger.info(msg)
            return

        # Обычный режим (полная информация)
        entry = {
            "timestamp": timestamp,
            "path": path,
            "reason": reason,
            "type": value_type,
            "app_name": app_name if app_name is not None else self.app_name,
        }
        if value is not None:
            entry["hash"] = self._hash_value(value)

        if self.custom_handler is not None:
            self.custom_handler(entry)
            return

        if self.format == 'json':
            self.logger.info(json.dumps(entry))
        else:
            msg = f"Значение маски '{path}' | reason={reason} | type={value_type}"
            self.logger.info(msg)
