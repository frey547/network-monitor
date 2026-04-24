from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.anomaly import Anomaly
from app.models.event import Event
from app.models.metric import Metric
from app.storage.database import AnomalyORM, EventORM, MetricORM, SessionLocal
from app.storage.memory import InMemoryStore


class Repository(ABC):
    @abstractmethod
    def add_metric(self, metric: Metric) -> None:
        pass

    @abstractmethod
    def add_anomaly(self, anomaly: Anomaly) -> None:
        pass

    @abstractmethod
    def add_event(self, event: Event) -> None:
        pass

    @abstractmethod
    def update_event_status(self, event_id: str, status: str) -> Optional[Event]:
        pass

    @abstractmethod
    def get_recent_metrics(self, limit: Optional[int] = None) -> List[Metric]:
        pass

    @abstractmethod
    def get_events(self) -> List[Event]:
        pass

    @abstractmethod
    def get_anomalies(self) -> List[Anomaly]:
        pass


class InMemoryRepository(Repository):
    def __init__(self, store: InMemoryStore):
        self.store = store

    def add_metric(self, metric: Metric) -> None:
        self.store.metrics.append(metric)

    def add_anomaly(self, anomaly: Anomaly) -> None:
        self.store.anomalies.append(anomaly)

    def add_event(self, event: Event) -> None:
        self.store.events.append(event)

    def update_event_status(self, event_id: str, status: str) -> Optional[Event]:
        for event in self.store.events:
            if event.event_id == event_id:
                event.status = status
                return event
        return None

    def get_recent_metrics(self, limit: Optional[int] = None) -> List[Metric]:
        data = sorted(self.store.metrics, key=lambda x: x.timestamp)
        if limit is None:
            return data
        return data[-limit:]

    def get_events(self) -> List[Event]:
        return list(self.store.events)

    def get_anomalies(self) -> List[Anomaly]:
        return list(self.store.anomalies)


class SQLiteRepository(Repository):
    def add_metric(self, metric: Metric) -> None:
        with SessionLocal() as session:
            session.add(
                MetricORM(
                    timestamp=metric.timestamp,
                    name=metric.name,
                    value=metric.value,
                    labels=metric.labels,
                )
            )
            session.commit()

    def add_anomaly(self, anomaly: Anomaly) -> None:
        with SessionLocal() as session:
            session.add(
                AnomalyORM(
                    timestamp=anomaly.timestamp,
                    metric=anomaly.metric,
                    value=anomaly.value,
                    is_anomaly=anomaly.is_anomaly,
                    score=anomaly.score,
                    baseline=anomaly.baseline,
                )
            )
            session.commit()

    def add_event(self, event: Event) -> None:
        with SessionLocal() as session:
            session.add(
                EventORM(
                    event_id=event.event_id,
                    metric=event.metric,
                    source=event.source,
                    severity=event.severity,
                    status=event.status,
                    timestamp=event.timestamp,
                )
            )
            session.commit()

    def update_event_status(self, event_id: str, status: str) -> Optional[Event]:
        with SessionLocal() as session:
            row = session.query(EventORM).filter(EventORM.event_id == event_id).first()
            if row is None:
                return None
            row.status = status
            session.commit()
            return Event(
                event_id=row.event_id,
                metric=row.metric,
                source=row.source,
                severity=row.severity,
                status=row.status,
                timestamp=row.timestamp,
            )

    def get_recent_metrics(self, limit: Optional[int] = None) -> List[Metric]:
        with SessionLocal() as session:
            query = session.query(MetricORM).order_by(MetricORM.timestamp.asc())
            if limit is not None:
                rows = query.limit(limit).all()
            else:
                rows = query.all()
            return [
                Metric(
                    timestamp=row.timestamp,
                    name=row.name,
                    value=row.value,
                    labels=row.labels or {},
                )
                for row in rows
            ]

    def get_events(self) -> List[Event]:
        with SessionLocal() as session:
            rows = session.query(EventORM).order_by(EventORM.timestamp.asc()).all()
            return [
                Event(
                    event_id=row.event_id,
                    metric=row.metric,
                    source=row.source,
                    severity=row.severity,
                    status=row.status,
                    timestamp=row.timestamp,
                )
                for row in rows
            ]

    def get_anomalies(self) -> List[Anomaly]:
        with SessionLocal() as session:
            rows = session.query(AnomalyORM).order_by(AnomalyORM.timestamp.asc()).all()
            return [
                Anomaly(
                    timestamp=row.timestamp,
                    metric=row.metric,
                    value=row.value,
                    is_anomaly=row.is_anomaly,
                    score=row.score,
                    baseline=row.baseline,
                )
                for row in rows
            ]
