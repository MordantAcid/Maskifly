import json
import logging
import django
from typing import Any, Dict, Optional, Union

from django.conf import settings
from django.http import HttpRequest, QueryDict
from django.utils.deprecation import MiddlewareMixin

from maskinfly import Masker

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "mask_char": "*",
    "mask_length": 3,
    "deep_mask": False,
    "audit_enabled": False,
    "auto_varname": False,
    # можно передать любые другие параметры Masker
}


def get_masker_from_settings() -> Masker:
    """Создаёт экземпляр Masker на основе настроек Django."""
    config = getattr(settings, "MASKINFLY", {}).copy()
    # объединяем с дефолтными значениями
    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)
    return Masker(**config)


class MaskingMiddleware(MiddlewareMixin):
    """
    Middleware для маскировки чувствительных данных во входящем запросе.

    - Маскирует значения в request.GET и request.POST (QueryDict).
    - При наличии заголовка Content-Type: application/json маскирует также
      загруженный JSON (request._json_cache).

    Использование в settings.py:
        MIDDLEWARE = [
            ...
            'maskinfly.contrib.django.MaskingMiddleware',
        ]
        MASKINFLY = {
            'mask_char': '#',
            'mask_length': 5,
            'audit_enabled': True,
        }
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.masker = get_masker_from_settings()

    def _mask_querydict(self, qdict: QueryDict) -> QueryDict:
        """Возвращает новый QueryDict с замаскированными значениями."""
        if not qdict:
            return qdict
        new_qd = QueryDict(mutable=True)
        for key, values in qdict.lists():
            masked_values = [self.masker.mask(v, path=key) for v in values]
            new_qd.setlist(key, masked_values)
        return new_qd

    def _mask_json_body(self, request: HttpRequest) -> None:
        """
        Если тело запроса – JSON и уже разобрано (например, DRF или django.request),
        маскирует его рекурсивно и сохраняет в request._json_cache.
        """
        json_cache = getattr(request, '_json_cache', None)
        if json_cache is None:
            return
        try:
            masked = self.masker.mask(json_cache)
            setattr(request, '_json_cache', masked)
        except Exception as e:
            logger.warning("Не удалось замаскировать JSON тело запроса: %s", e)

    def process_request(self, request: HttpRequest) -> None:
        # Маскируем GET и POST
        if request.GET:
            request.GET = self._mask_querydict(request.GET)
        if request.POST:
            request.POST = self._mask_querydict(request.POST)

        # Маскируем разобранное JSON тело (например, от DRF или django-rest-framework)
        self._mask_json_body(request)


def apply_mask_to_request(request: HttpRequest, masker: Optional[Masker] = None) -> None:
    """
    Утилита для ручного применения маскировки к уже существующему запросу.
    Может использоваться в декораторах представлений или кастомном middleware.
    """
    if masker is None:
        masker = get_masker_from_settings()

    # Маскируем GET
    if request.GET:
        new_get = QueryDict(mutable=True)
        for key, values in request.GET.lists():
            masked_values = [masker.mask(v, path=key) for v in values]
            new_get.setlist(key, masked_values)
        request.GET = new_get

    # Маскируем POST
    if request.POST:
        new_post = QueryDict(mutable=True)
        for key, values in request.POST.lists():
            masked_values = [masker.mask(v, path=key) for v in values]
            new_post.setlist(key, masked_values)
        request.POST = new_post

    # Маскируем JSON тело, если оно уже разобрано
    json_cache = getattr(request, '_json_cache', None)
    if json_cache is not None:
        setattr(request, '_json_cache', masker.mask(json_cache))
