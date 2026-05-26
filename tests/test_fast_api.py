import json
import pytest
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from starlette.testclient import TestClient
from maskinfly import Masker
from maskinfly.contrib.fastapi import (
    MaskResponseMiddleware,
    mask_response,
    setup_fastapi_masking,
)

@pytest.fixture
def app():
    return FastAPI()


# Убираем фикстуру client, будем создавать его в каждом тесте

def test_mask_response_middleware_basic(app):
    """Middleware маскирует JSON-ответ по умолчанию."""
    @app.get("/secret")
    async def secret():
        return {"password": "secret123", "user": "alice"}

    app.add_middleware(MaskResponseMiddleware)
    client = TestClient(app)
    response = client.get("/secret")
    assert response.status_code == 200
    data = response.json()
    assert data["password"] == "***"
    assert data["user"] == "alice"


def test_mask_response_middleware_custom_masker(app):
    """Можно передать свой экземпляр Masker в middleware."""
    custom_masker = Masker(mask_char="#", mask_length=4)
    @app.get("/token")
    async def token():
        return {"token": "abcdef"}

    app.add_middleware(MaskResponseMiddleware, masker=custom_masker)
    client = TestClient(app)
    response = client.get("/token")
    assert response.json()["token"] == "####"


def test_mask_response_middleware_exclude_paths(app):
    """Пути из exclude_paths не маскируются."""
    @app.get("/public")
    async def public():
        return {"api_key": "public_key"}

    @app.get("/private")
    async def private():
        return {"api_key": "private_key"}

    app.add_middleware(MaskResponseMiddleware, exclude_paths=["/public"])
    client = TestClient(app)
    response_public = client.get("/public")
    assert response_public.json()["api_key"] == "public_key"
    response_private = client.get("/private")
    assert response_private.json()["api_key"] == "***"


def test_mask_response_middleware_non_json_response(app):
    """Не-JSON ответы (например, текст) не маскируются."""
    @app.get("/text", response_class=PlainTextResponse)
    async def text():
        return "plain text"

    app.add_middleware(MaskResponseMiddleware)
    client = TestClient(app)
    response = client.get("/text")
    assert response.text == "plain text"


def test_mask_response_middleware_masking_error(app):
    """При ошибке в маскере middleware возвращает исходный ответ без изменений."""
    class BrokenMasker:
        def mask(self, data, *args, **kwargs):
            raise Exception("masking error")

    @app.get("/error-endpoint")
    async def error_endpoint():
        return {"secret": "value"}

    app.add_middleware(MaskResponseMiddleware, masker=BrokenMasker())
    client = TestClient(app)
    response = client.get("/error-endpoint")
    assert response.status_code == 200
    assert response.json() == {"secret": "value"}


def test_mask_response_decorator_sync():
    """Декоратор mask_response для синхронной функции."""
    @mask_response(mask_char="#", mask_length=2)
    def get_data():
        return {"password": "supersecret"}

    result = get_data()
    assert result == {"password": "##"}


@pytest.mark.asyncio
async def test_mask_response_decorator_async():
    """Декоратор mask_response для асинхронной функции."""
    @mask_response(mask_char="X", mask_length=5)
    async def get_token():
        return {"token": "abc123"}

    result = await get_token()
    assert result == {"token": "XXXXX"}


def test_mask_response_decorator_with_explicit_masker():
    """Декоратор может принимать готовый экземпляр Masker."""
    masker = Masker(mask_char="*", mask_length=1)
    @mask_response(masker=masker)
    def func():
        # Возвращаем данные, которые действительно маскируются (пароль)
        return {"password": "secret"}

    assert func() == {"password": "*"}


def test_setup_fastapi_masking(app):
    """setup_fastapi_masking добавляет middleware в приложение."""
    @app.get("/secret")
    async def secret():
        return {"api_key": "value"}

    setup_fastapi_masking(app, exclude_paths=["/health"])
    @app.get("/health")
    async def health():
        return {"api_key": "health_key"}

    client = TestClient(app)
    response_secret = client.get("/secret")
    assert response_secret.json()["api_key"] == "***"
    response_health = client.get("/health")
    assert response_health.json()["api_key"] == "health_key"
