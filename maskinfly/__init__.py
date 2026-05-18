from maskinfly.masker import Masker
from maskinfly.audit import AuditLogger
from maskinfly.tensor import Tensor
from maskinfly.autograd import no_grad
from maskinfly import nn
from maskinfly import optim
from typing import Optional, Dict, Tuple, Callable, Pattern

__all__ = [
    "mask", "AuditLogger", "Masker",
    "Tensor", "no_grad", "nn", "optim"
]

__version__ = "0.1.5"  # Обновляем версию

def mask(data,
         audit_enabled: bool = False,
         audit_logger: Optional[AuditLogger] = None,
         auto_varname: bool = False,
         var_name: Optional[str] = None,
         mask_char: str = "*",
         mask_length: int = 3,
         custom_patterns: Optional[Dict[str, Tuple[Pattern, Callable]]] = None):
    """
    Основной удобный интерфейс для маскировки данных.

    Примеры:
        >>> mask({"user": "john", "password": "secret123"})
        {'user': 'john', 'password': '***'}

        >>> mask("user@example.com", mask_char='#', mask_length=2)
        'u##@example.com'

        >>> mask("My token is abc123", audit_enabled=True)
        'My token is ***'

    Args:
        data: любые данные (строка, dict, список и т.д.)
        audit_enabled: включить логирование аудита
        audit_logger: свой экземпляр AuditLogger (опционально)
        auto_varname: автоматически определять имя переменной (медленно)
        var_name: явное имя переменной для маскировки
        mask_char: символ маски (по умолчанию '*')
        mask_length: длина маски (по умолчанию 3)
        custom_patterns: словарь дополнительных паттернов вида
                        {name: (regex_pattern, replace_func)}.
                        replace_func должна принимать (match, mask_char, mask_length)

    Returns:
        замаскированная копия данных
    """
    masker = Masker(
        audit_enabled=audit_enabled,
        audit_logger=audit_logger,
        auto_varname=auto_varname,
        mask_char=mask_char,
        mask_length=mask_length,
        custom_patterns=custom_patterns
    )
    return masker.mask(data, var_name=var_name)
