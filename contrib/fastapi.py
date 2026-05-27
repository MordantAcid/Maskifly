# contrib/fastapi.py
import json
import logging
from typing import Any, Callable, Optional

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
from starlette.exceptions import HTTPException

from maskinfly import Masker

DEFAULT_MASKER = Masker()
logger = logging.getLogger(__name__)


class MaskResponseMiddleware(BaseHTTPMiddleware):
    """
    Middleware для маскировки JSON-ответов FastAPI с ограничением размера ответа.
    """

    def __init__(
        self,
        app: ASGIApp,
        masker: Optional[Masker] = None,
        exclude_paths: Optional[list[str]] = None,
        max_size_bytes: int = 10 * 1024 * 1024,   # 10 MB
        skip_on_too_large: bool = True,
    ):
        super().__init__(app)
        self.masker = masker or DEFAULT_MASKER
        self.exclude_paths = exclude_paths or []
        self.max_size_bytes = max_size_bytes
        self.skip_on_too_large = skip_on_too_large

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        response = await call_next(request)

        content_type = response.headers.get('content-type', '')
        if not content_type.startswith('application/json'):
            return response

        # Проверка размера ответа по заголовку Content-Length
        content_length = response.headers.get('content-length')
        if content_length is not None:
            try:
                size = int(content_length)
                if size > self.max_size_bytes:
                    if self.skip_on_too_large:
                        logger.warning(
                            f"Response size {size} bytes exceeds limit {self.max_size_bytes}, skipping masking for {request.url.path}"
                        )
                        return response
                    else:
                        # Возвращаем 413 Payload Too Large
                        return JSONResponse(
                            status_code=413,
                            content={"detail": "Response payload too large for masking"},
                        )
            except ValueError:
                pass  # некорректный заголовок – игнорируем

        # Если Content-Length отсутствует (chunked encoding) – пропускаем маскировку
        if content_length is None:
            logger.debug(
                f"Response without Content-Length (chunked) for {request.url.path}, skipping masking"
            )
            return response

        # Теперь безопасно читаем тело (размер уже проверен)
        body = b''
        async for chunk in response.body_iterator:
            body += chunk
            if len(body) > self.max_size_bytes:
                # Эта проверка на случай, если Content-Length был неверным
                if self.skip_on_too_large:
                    logger.warning(
                        f"Response exceeded limit while reading, skipping masking for {request.url.path}"
                    )
                    return response
                else:
                    return JSONResponse(
                        status_code=413,
                        content={"detail": "Response payload too large for masking"},
                    )

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
            # В случае ошибки возвращаем исходный ответ
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )


def mask_response(
    masker: Optional[Masker] = None, **masker_kwargs
) -> Callable[[Callable], Callable]:
    """
    Декоратор для маскировки возвращаемого значения обработчика.
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
    max_size_bytes: int = 10 * 1024 * 1024,
    skip_on_too_large: bool = True,
) -> None:
    """
    Добавляет MaskResponseMiddleware во всё приложение FastAPI.

    :param max_size_bytes: максимальный размер JSON-ответа (в байтах), который будет замаскирован.
    :param skip_on_too_large: если True, при превышении размера маскировка пропускается (ответ возвращается как есть);
                              если False, возвращается HTTP 413 Payload Too Large.
    """
    app.add_middleware(
        MaskResponseMiddleware,
        masker=masker,
        exclude_paths=exclude_paths,
        max_size_bytes=max_size_bytes,
        skip_on_too_large=skip_on_too_large,
    )
