from dataclasses import asdict, dataclass


@dataclass
class Event:
    event_id: str
    metric: str
    source: str
    severity: str
    status: str
    timestamp: float

    def to_dict(self):
        return asdict(self)
