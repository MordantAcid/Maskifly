from maskinfly.masker import Masker
from maskinfly.audit import AuditLogger
from maskinfly.tensor import Tensor
from maskinfly.autograd import no_grad
from maskinfly import nn
from maskinfly import optim
from typing import Optional

__all__ = [
    "mask", "AuditLogger", "Masker",
    "Tensor", "no_grad", "nn", "optim"
]

__version__ = "0.1.3"

def mask(data, audit_enabled: bool = False, audit_logger: Optional[AuditLogger] = None, auto_varname: bool = False, var_name: Optional[str] = None):
    """Основной удобный интерфейс для маскировки данных.
    
    Примеры:
        >>> mask({"user": "john", "password", "secret123"})
        {'user': 'john', 'password': '***'}

        >>> mask("My token is abc123xyz", audit_enabled=True)
        'My token is ***'
    Args:
        data: любые данные (строка, dict, список и т.д.)
        audit_enabled: включить логирование аудита
        audit_logger: свой экземпляр AuditLogger (опционально)

    Returns:
        замаскированная копия данных
    """
    masker = Masker(audit_enabled=audit_enabled, audit_logger=audit_logger, auto_varname=auto_varname)
    return masker.mask(data, var_name=var_name)
