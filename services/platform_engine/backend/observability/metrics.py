from collections import defaultdict
from dataclasses import dataclass

@dataclass
class Counter:
    value: int = 0
    def inc(self, amount: int = 1): self.value += amount

class MetricsRegistry:
    def __init__(self): self.counters = defaultdict(Counter)
    def inc(self, name: str, amount: int = 1): self.counters[name].inc(amount)
    def snapshot(self): return {k:v.value for k,v in self.counters.items()}
