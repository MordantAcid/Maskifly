import re
from maskinfly.patterns import PATTERNS, DEFAULT_MASK

def test_patterns_are_compile():
    for name, pattern in PATTERNS.items():
        assert isinstance(pattern, re.Pattern), f"Паттерн {name} не скомпилирован"

def test_password_pattern():
    pattern = PATTERNS["password"]
    match = pattern.search("password=12345")
    assert match is not None
    groups = match.groups()
    assert len(groups) == 3
    assert groups[2] == "12345"

def test_token_pattern():
    pattern = PATTERNS["token"]
    match = pattern.search("token=abc123")
    assert match is not None
    groups = match.groups()
    assert groups[2] == "abc123"

def test_email_pattern():
    pattern = PATTERNS["email"]
    assert pattern.search("user@example.com") is not None
    assert pattern.search("Недействительный") is None

def test_jwt_pattern():
    pattern = PATTERNS["jwt"]
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    assert pattern.search(jwt) is not None

def test_ip_pattern():
    pattern = PATTERNS["ip"]
    assert pattern.search("192.168.1.1") is not None
    assert pattern.search("999.999.999.999") is None
    assert pattern.search("256.0.0.1") is None