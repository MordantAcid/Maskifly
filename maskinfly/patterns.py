import re

PATTERNS = {
    "password": re.compile(r'(?i)(password|passwd|pwd)(\s*[:=]\s*)(\S+)'),
    "token": re.compile(r'(?i)(token|api_key|apikey)(\s*[:=]\s*)(\S+)'),
    "credit_card": re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b'),
    "email": re.compile(r'\b[\w\.-]+@[\w\.-]+\.\w+\b'),
    "jwt": re.compile(r'eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+'),
    "ip": re.compile(r'\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
}

DEFAULT_MASK = "***"