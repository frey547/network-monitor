from dataclasses import asdict, dataclass, field
from typing import Dict


@dataclass
class Metric:
    timestamp: float
    name: str
    value: float
    labels: Dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)
