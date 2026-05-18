import inspect
from typing import Any, Optional

def find_variable_name(value: Any, frame_depth: int = 2) -> Optional[str]:
    frame = inspect.currentframe()
    try:
        for _ in range(frame_depth):
            if frame is None:
                return None
            frame = frame.f_back
        if frame is None:
            return None

        value_id = id(value)
        # Сначала ищем в locals
        for name, val in frame.f_locals.items():
            if id(val) == value_id:
                return name
        # Потом в globals
        for name, val in frame.f_globals.items():
            if id(val) == value_id:
                return name
    finally:
        del frame
    return None

SENSITIVE_VAR_NAMES = {
    'password', 'passwd', 'pwd', 'secret', 'token', 'api_key', 'apikey',
    'credit_card', 'creditcard', 'card_number', 'ssn', 'social_security',
    'pin', 'auth', 'bearer', 'private_key'
}
