import json
import pytest
from unittest.mock import patch, Mock, MagicMock
from django.http import HttpRequest, QueryDict, HttpResponse
from django.test import RequestFactory
from maskinfly.contrib.django import get_masker_from_settings, MaskingMiddleware, apply_mask_to_request
from maskinfly import Masker
from django.test import override_settings


@pytest.fixture
def rf():
    """RequestFactory для создания запросов."""
    return RequestFactory()

def test_get_masker_from_settings_default():
    from django.conf import settings
    # сохраняем оригинальную настройку
    original = getattr(settings, 'MASKINFLY', None)
    try:
        if hasattr(settings, 'MASKINFLY'):
            delattr(settings, 'MASKINFLY')
        masker = get_masker_from_settings()
        assert masker.mask_char == '*'
    finally:
        if original is not None:
            settings.MASKINFLY = original

def test_get_masker_from_settings_custom():
    """Параметры из MASKINFLY передаются в Masker."""
    with override_settings(MASKINFLY={
        "mask_char": "#",
        "mask_length": 5,
        "audit_enabled": True,
        "deep_mask": True,
    }):
        masker = get_masker_from_settings()
        assert masker.mask_char == "#"
        assert masker.mask_length == 5
        assert masker.audit_enabled is True
        assert masker.deep_mask is True

def test_masking_middleware_get_params(rf):
    """GET параметры маскируются."""
    middleware = MaskingMiddleware(lambda req: HttpResponse())
    request = rf.get("/", {"user": "alice", "password": "secret123"})
    middleware.process_request(request)
    assert request.GET["user"] == "alice"
    assert request.GET["password"] == "***"


def test_masking_middleware_post_params(rf):
    """POST параметры маскируются."""
    middleware = MaskingMiddleware(lambda req: HttpResponse())
    request = rf.post("/", {"token": "abc123", "safe": "value"})
    middleware.process_request(request)
    assert request.POST["token"] == "***"
    assert request.POST["safe"] == "value"


def test_masking_middleware_json_body(rf):
    """JSON тело (request._json_cache) маскируется."""
    middleware = MaskingMiddleware(lambda req: HttpResponse())
    request = rf.post("/", data=json.dumps({"api_key": "xyz", "data": "ok"}), content_type="application/json")
    # Имитируем, что DRF или другой парсер уже разобрал JSON и сохранил в _json_cache
    request._json_cache = {"api_key": "xyz", "data": "ok"}
    middleware.process_request(request)
    assert request._json_cache["api_key"] == "***"
    assert request._json_cache["data"] == "ok"


def test_masking_middleware_json_body_error(rf, caplog):
    """При ошибке маскировки JSON тело не изменяется, логирование не требуется, так как ошибки не возникает."""
    middleware = MaskingMiddleware(lambda req: HttpResponse())
    request = rf.post("/")
    request._json_cache = {"bad": object()}  # несериализуемый объект
    middleware.process_request(request)
    # Masker.mask обрабатывает объекты без ошибок, поэтому _json_cache остаётся неизменным
    assert request._json_cache["bad"] is not None
    # Предупреждение не логгируется, так как исключения нет


def test_masking_middleware_skip_empty(rf):
    """Если GET/POST пусты, ничего не ломается."""
    middleware = MaskingMiddleware(lambda req: HttpResponse())
    request = rf.get("/")
    middleware.process_request(request)
    assert request.GET == {}
    assert request.POST == {}


def test_apply_mask_to_request(rf):
    """Функция apply_mask_to_request маскирует запрос аналогично middleware."""
    request = rf.get("/", {"pwd": "secret", "user": "john"})
    apply_mask_to_request(request)
    assert request.GET["pwd"] == "***"
    assert request.GET["user"] == "john"
    # POST отсутствует
    # JSON тело
    request._json_cache = {"token": "123"}
    apply_mask_to_request(request)
    assert request._json_cache["token"] == "***"


def test_apply_mask_to_request_with_custom_masker(rf):
    """Можно передать свой экземпляр Masker."""
    custom_masker = Masker(mask_char="#", mask_length=2)
    request = rf.get("/", {"api_key": "abc"})
    apply_mask_to_request(request, masker=custom_masker)
    assert request.GET["api_key"] == "##"
