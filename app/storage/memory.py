from dataclasses import dataclass, field
from typing import List

from app.models.anomaly import Anomaly
from app.models.event import Event
from app.models.metric import Metric


@dataclass
class InMemoryStore:
    metrics: List[Metric] = field(default_factory=list)
    anomalies: List[Anomaly] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
