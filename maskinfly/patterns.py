import re

from typing import Callable, Tuple, Dict, Any

def full_mask_replacer(match: re.Match, mask_char: str, mask_length: int) -> str:
    """Заменяет все совпадения на маску."""
    return mask_char * mask_length

def email_mask_replacer(match: re.Match, mask_char: str, mask_length: int) -> str:
    """Частичная маскировка email: локальная часть -> первый символ + маска.
    
    Пример: user@example.com -> u**@example.com
    """
    local = match.group(1)
    domain = match.group(2)
    if len(local) <= 1:
        masked_local = mask_char * mask_length
    else:
        masked_local = local[0] + mask_char * mask_length
    return f"{masked_local}@{domain}"

def key_value_mask_replacer(match: re.Match, mask_char: str, mask_length: int) -> str:
    """Заменяет только значение (группа 3) в паттернах ключ=значение."""
    key = match.group(1)
    separator = match.group(2)
    return f"{key}{separator}{mask_char * mask_length}"

# Паттерны
PATTERNS: Dict[str, Tuple[re.Pattern, Callable]] = {
    "password": (re.compile(r'(?i)(password|passwd|pwd)(\s*[:=]\s*)(\S+)'), key_value_mask_replacer),
    "token": (re.compile(r'(?i)(token|api_key|apikey)(\s*[:=]\s*)(\S+)'), key_value_mask_replacer),
    "credit_card": (re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'), full_mask_replacer),
    "email": (re.compile(r'\b([\w\.-]+)@([\w\.-]+\.\w+)\b'), email_mask_replacer),
    "jwt": (re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'), full_mask_replacer),
    "ip": (re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'), full_mask_replacer),
    "ssn": (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), full_mask_replacer),
}

DEFAULT_MASK_CHAR = "*"
DEFAULT_MASK_LENGTH = 3
