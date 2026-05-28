import logging
import json
import hashlib
import threading
import queue
import asyncio
import warnings
from datetime import datetime
from typing import Optional, Callable, Dict, Any, Awaitable

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
                 safe_mode: bool = False,
                 async_mode: bool = False,
                 async_handler: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
                 queue_maxsize: int = 0,
                 drop_on_full: bool = False,          # будет проигнорировано в async_mode
                 queue_timeout: float = 0.1):         # не используется в async_mode

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
        self.async_mode = async_mode

        # Для асинхронного режима всегда используем неблокирующую вставку
        if self.async_mode:
            if not drop_on_full:
                warnings.warn(
                    "async_mode=True и drop_on_full=False несовместимы: в асинхронном режиме "
                    "всегда используется неблокирующая вставка (put_nowait). drop_on_full принудительно установлен в True.",
                    UserWarning
                )
            self.drop_on_full = True          # принудительно
            self.queue_maxsize = queue_maxsize
            self._queue = queue.Queue(maxsize=queue_maxsize)
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._worker, daemon=True)
            self._thread.start()
        else:
            # Синхронный режим – параметры drop_on_full/queue_timeout не используются
            self.drop_on_full = drop_on_full
            self.queue_timeout = queue_timeout

        self.async_handler = async_handler

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

    def _process_entry(self, entry: Dict[str, Any]) -> None:
        """Синхронная обработка записи (вызов custom_handler или логирование)."""
        if self.custom_handler is not None:
            self.custom_handler(entry)
            return

        if self.format == 'json':
            self.logger.info(json.dumps(entry))
        else:
            if self.safe_mode:
                msg = f"MASKING EVENT hash={entry.get('hash', '')}"
            else:
                msg = f"Значение маски '{entry.get('path', '')}' | reason={entry.get('reason', '')} | type={entry.get('type', '')}"
            self.logger.info(msg)

    def _worker(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        while not self._stop_event.is_set() or not self._queue.empty():
            try:
                entry = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                if self.async_handler is not None:
                    loop.run_until_complete(self.async_handler(entry))
                else:
                    self._process_entry(entry)
            except Exception:
                pass
        loop.close()

    def log(self,
            path: str,
            reason: str,
            value_type: str,
            value: Any = None,
            app_name: Optional[str] = None) -> None:
        timestamp = datetime.now().isoformat()

        if self.safe_mode:
            entry = {
                "timestamp": timestamp,
                "hash": self._hash_value(value),
            }
        else:
            entry = {
                "timestamp": timestamp,
                "path": path,
                "reason": reason,
                "type": value_type,
                "app_name": app_name if app_name is not None else self.app_name,
            }
            if value is not None:
                entry["hash"] = self._hash_value(value)

        if self.async_mode:
            # Всегда неблокирующая вставка (fire-and-forget)
            try:
                self._queue.put_nowait(entry)
            except queue.Full:
                self.logger.warning(
                    f"Audit queue full (maxsize={self.queue_maxsize}), event dropped: path={path}, reason={reason}"
                )
        else:
            self._process_entry(entry)

    def stop(self, timeout: float = 5.0) -> None:
        """Останавливает фоновый поток и дожидается обработки оставшихся записей."""
        if not self.async_mode:
            return
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
