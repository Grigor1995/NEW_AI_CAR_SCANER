from contextlib import contextmanager
from dataclasses import dataclass, field
from time import perf_counter

@dataclass
class Span:
    name: str
    attributes: dict = field(default_factory=dict)
    duration_ms: float = 0.0

@contextmanager
def span(name: str, **attributes):
    s = Span(name, attributes); start = perf_counter()
    try: yield s
    finally: s.duration_ms = (perf_counter()-start)*1000
