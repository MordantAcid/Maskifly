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
}


def get_masker_from_settings() -> Masker:
    """Создаёт экземпляр Masker на основе настроек Django."""
    config = getattr(settings, "MASKINFLY", {}).copy()
    for key, value in DEFAULT_CONFIG.items():
        config.setdefault(key, value)
    return Masker(**config)


class MaskingMiddleware(MiddlewareMixin):
    """
    Middleware для маскировки чувствительных данных во входящем запросе.
    """

    def __init__(self, get_response):
        super().__init__(get_response)
        self.masker = get_masker_from_settings()

    def _mask_querydict(self, qdict: QueryDict) -> QueryDict:
        if not qdict:
            return qdict
        new_qd = QueryDict(mutable=True)
        for key, values in qdict.lists():
            masked_values = [self.masker.mask(v, path=key) for v in values]
            new_qd.setlist(key, masked_values)
        return new_qd

    def _mask_json_body(self, request: HttpRequest) -> None:
        """
        Маскирует только словари и списки в _json_cache.
        Простые типы (str, int и т.д.) не нуждаются в рекурсивной маскировке.
        """
        json_cache = getattr(request, '_json_cache', None)
        if json_cache is None:
            return
        # Если это словарь или список – применяем маскировку
        if isinstance(json_cache, (dict, list)):
            try:
                masked = self.masker.mask(json_cache)
                setattr(request, '_json_cache', masked)
            except Exception as e:
                logger.warning("Не удалось замаскировать JSON тело запроса: %s", e)
        # Для простых типов ничего не делаем – они уже не содержат конфиденциальных вложенных структур

    def process_request(self, request: HttpRequest) -> None:
        if request.GET:
            request.GET = self._mask_querydict(request.GET)
        if request.POST:
            request.POST = self._mask_querydict(request.POST)
        self._mask_json_body(request)


def apply_mask_to_request(request: HttpRequest, masker: Optional[Masker] = None) -> None:
    """
    Утилита для ручного применения маскировки к уже существующему запросу.
    """
    if masker is None:
        masker = get_masker_from_settings()

    if request.GET:
        new_get = QueryDict(mutable=True)
        for key, values in request.GET.lists():
            masked_values = [masker.mask(v, path=key) for v in values]
            new_get.setlist(key, masked_values)
        request.GET = new_get

    if request.POST:
        new_post = QueryDict(mutable=True)
        for key, values in request.POST.lists():
            masked_values = [masker.mask(v, path=key) for v in values]
            new_post.setlist(key, masked_values)
        request.POST = new_post

    json_cache = getattr(request, '_json_cache', None)
    if json_cache is not None and isinstance(json_cache, (dict, list)):
        setattr(request, '_json_cache', masker.mask(json_cache))
