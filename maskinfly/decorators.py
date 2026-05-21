import functools
import inspect

from typing import Any, Callable, Dict, Optional, Tuple, Pattern, Union, Awaitable
from maskinfly import Masker, AuditLogger

def mask_output(
    audit_enabled: bool = False,
    audit_logger: Optional[AuditLogger] = None,
    auto_varname: bool = False,
    mask_char: str = "*",
    mask_length: int = 3,
    custom_patterns: Optional[Dict[str, Tuple[Pattern, Callable]]] = None,
    audit_format: str = 'text',
    audit_custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
    audit_app_name: Optional[str] = None,
    deep_mask: bool = False,
) -> Callable:
    """
    Декоратор для маскировки возвращаемого значения функции.

    Аргументы те же, что и у функции mask() из maskinfly.

    Пример:
        @mask_output(audit_enabled=True, mask_char='#', mask_length=4)
        def get_user():
            return {"name": "Alice", "password": "secret123"}

        result = get_user()  # {'name': 'Alice', 'password': '####'}
    """
    def decorator(func: Callable) -> Callable:
        # Создаём один экземпляр Masker для всех вызовов функции
        masker = Masker(
            audit_enabled=audit_enabled,
            audit_logger=audit_logger,
            auto_varname=auto_varname,
            mask_char=mask_char,
            mask_length=mask_length,
            custom_patterns=custom_patterns,
            audit_format=audit_format,
            audit_custom_handler=audit_custom_handler,
            audit_app_name=audit_app_name,
            deep_mask=deep_mask,
        )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            result = func(*args, **kwargs)
            return masker.mask(result)

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            result = await func(*args, **kwargs)
            return masker.mask(result)

        # Используем inspect.iscoroutinefunction
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
