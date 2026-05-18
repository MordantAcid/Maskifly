import logging
from typing import Optional

class AuditLogger:
    def __init__(self, logger: Optional[logging.Logger] = None):
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

    def log(self, path: str, reason: str, value_type: str) -> None:
        self.logger.info(f"Значение маски '{path}' | reason={reason} | type={value_type}")
