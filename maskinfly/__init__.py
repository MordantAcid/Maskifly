from maskinfly.masker import Masker
from maskinfly.audit import AuditLogger
from maskinfly.tensor import Tensor
from maskinfly.autograd import no_grad
from maskinfly import nn
from maskinfly import optim
from typing import Optional, Dict, Tuple, Callable, Pattern, Any

__all__ = [
    "mask", "AuditLogger", "Masker",
    "Tensor", "no_grad", "nn", "optim"
]

__version__ = "0.1.8"  # Обновляем версию

def mask(data,
         audit_enabled: bool = False,
         audit_logger: Optional[AuditLogger] = None,
         auto_varname: bool = False,
         var_name: Optional[str] = None,
         mask_char: str = "*",
         mask_length: int = 3,
         custom_patterns: Optional[Dict[str, Tuple[Pattern, Callable]]] = None,
         audit_format: str = 'text',
         audit_custom_handler: Optional[Callable[[Dict[str, Any]], None]] = None,
         audit_app_name: Optional[str] = None,
         deep_mask: bool = False):   # новый параметр
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
        deep_mask=deep_mask          # передаём
    )
    return masker.mask(data, var_name=var_name)
