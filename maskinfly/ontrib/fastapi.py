import json
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response, Depends
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from maskinfly import Masker

DEFAULT_MASKER = Masker()


class MaskResponseMiddleware(BaseHTTPMiddleware):
    """
    Middleware для маскировки JSON-ответов FastAPI.
    Перехватывает ответ, если это JSONResponse, и маскирует его содержимое.
    """

    def __init__(
        self,
        app: ASGIApp,
        masker: Optional[Masker] = None,
        exclude_paths: Optional[list[str]] = None,
    ):
        super().__init__(app)
        self.masker = masker or DEFAULT_MASKER
        self.exclude_paths = exclude_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Пропускаем исключённые пути
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        response = await call_next(request)

        # Проверяем, что это JSON-ответ по заголовку Content-Type
        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('application/json'):
            return response

        # Читаем тело ответа из асинхронного итератора
        body = b''
        async for chunk in response.body_iterator:
            body += chunk

        if not body:
            return response

        try:
            data = json.loads(body)
            masked_data = self.masker.mask(data)
            return JSONResponse(
                content=masked_data,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )
        except Exception:
            # В случае ошибки возвращаем исходный ответ (тело уже прочитано)
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )


def MaskResponseDependency(masker: Optional[Masker] = None):
    """
    Фабрика зависимости для маскировки возвращаемого значения обработчика.
    (Примечание: зависимости не могут изменить возвращаемое значение,
    поэтому рекомендуется использовать декоратор @mask_response или middleware.)
    """
    _masker = masker or DEFAULT_MASKER

    async def _dependency(response: Any) -> Any:
        return _masker.mask(response)

    return _dependency


def mask_response(
    masker: Optional[Masker] = None, **masker_kwargs
) -> Callable[[Callable], Callable]:
    """
    Декоратор для маскировки возвращаемого значения обработчика (синхронного или асинхронного).
    """
    if masker is None:
        local_masker = Masker(**masker_kwargs)
    else:
        local_masker = masker

    def decorator(func: Callable) -> Callable:
        async def async_wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            return local_masker.mask(result)

        def sync_wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            return local_masker.mask(result)

        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def setup_fastapi_masking(
    app: FastAPI,
    masker: Optional[Masker] = None,
    exclude_paths: Optional[list[str]] = None,
) -> None:
    """
    Добавляет MaskResponseMiddleware во всё приложение FastAPI.
    """
    app.add_middleware(
        MaskResponseMiddleware,
        masker=masker,
        exclude_paths=exclude_paths,
    )
