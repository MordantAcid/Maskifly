import re

from maskinfly.patterns import PATTERNS, DEFAULT_MASK_CHAR, DEFAULT_MASK_LENGTH

def test_patterns_are_compile():
    for name, (regex, _) in PATTERNS.items():
        assert isinstance(regex, re.Pattern), f"Паттерн {name} не скомпилирован"

def test_password_pattern():
    regex, _ = PATTERNS["password"]
    match = regex.search("password=12345")
    assert match is not None
    groups = match.groups()
    assert len(groups) == 3
    assert groups[2] == "12345"

def test_token_pattern():
    regex, _ = PATTERNS["token"]
    match = regex.search("token=abc123")
    assert match is not None
    groups = match.groups()
    assert groups[2] == "abc123"

def test_email_pattern():
    regex, _ = PATTERNS["email"]
    assert regex.search("user@example.com") is not None
    assert regex.search("Недействительный") is None

def test_jwt_pattern():
    regex, _ = PATTERNS["jwt"]
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
    assert regex.search(jwt) is not None

def test_ip_pattern():
    regex, _ = PATTERNS["ip"]
    assert regex.search("192.168.1.1") is not None
    assert regex.search("999.999.999.999") is None
    assert regex.search("256.0.0.1") is None
