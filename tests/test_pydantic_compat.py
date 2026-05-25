import pytest
from maskinfly import Masker

pytest.importorskip("pydantic")

def test_secret_str_masking():
    from pydantic import SecretStr
    secret = SecretStr("my_secret")
    masker = Masker()
    result = masker.mask(secret)
    assert result == "***"


def test_secret_str_in_dict():
    from pydantic import SecretStr
    data = {"user": "alice", "api_key": SecretStr("abc123")}
    masker = Masker()
    result = masker.mask(data)
    assert result["api_key"] == "***"
    assert result["user"] == "alice"
