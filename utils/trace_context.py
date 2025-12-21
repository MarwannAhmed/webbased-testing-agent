from contextvars import ContextVar
from typing import Optional

_trace_id: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)

def set_trace_id(trace_id: str) -> None:
    _trace_id.set(trace_id)

def get_trace_id() -> Optional[str]:
    return _trace_id.get()
