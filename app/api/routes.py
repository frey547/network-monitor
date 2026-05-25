from time import time
import uuid

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from prometheus_client import generate_latest

from app.models.anomaly import Anomaly
from app.models.event import Event
from app.models.metric import Metric

router = APIRouter()


@router.get("/metrics/history")
def get_metrics_history(request: Request, metric: str, limit: int = 100):
    repository = request.app.state.repository
    metrics = [item for item in repository.get_recent_metrics() if item.name == metric]
    return [
        {"timestamp": item.timestamp, "value": item.value}
        for item in metrics[-limit:]
    ]


@router.get("/metrics/app")
def get_metrics(request: Request):
    detector = request.app.state.detector
    repository = request.app.state.repository
    latest_metrics = {}

    for item in repository.get_recent_metrics():
        latest_metrics[item.name] = item
    now = time()
    result = {}
    for metric_name, metric in latest_metrics.items():
        r = detector.detect(metric_name, metric.value, now)
        result[metric_name] = {
            "value": metric.value,
            "z_score": r.score,
            "is_anomaly": r.is_anomaly
        }
    return result    
    


@router.get("/alerts")
def get_alerts(request: Request):
    repository = request.app.state.repository
    return [event.to_dict() for event in repository.get_events()]


@router.patch("/events/{event_id}")
def update_event_status(event_id: str, request: Request, status: str):
    repository = request.app.state.repository
    event = repository.update_event_status(event_id, status)
    if event is None:
        raise HTTPException(status_code=404, detail="Event not found")
    return event.to_dict()


@router.get("/simulate")
def simulate_anomaly(request: Request, metric: str = "cpu", value: float = 100):
    repository = request.app.state.repository
    detector = request.app.state.detector
    alert_manager = request.app.state.alert_manager
    timestamp = time()

    metric_record = Metric(timestamp=timestamp, name=metric, value=value, labels={})
    repository.add_metric(metric_record)

    detector.add(metric, value)
    raw = detector.detect(metric, value, timestamp)
    anomaly = Anomaly(
        timestamp=timestamp,
        metric=metric,
        value=value,
        is_anomaly=raw.is_anomaly,
        score=raw.score,
        baseline=raw.baseline,
    )
    repository.add_anomaly(anomaly)

    triggered = alert_manager.add_alert(metric, anomaly)
    if triggered:
        repository.add_event(Event(
            event_id=str(uuid.uuid4()),
            metric=metric,
            source="localhost",
            severity="warning",
            status="open",
            timestamp=timestamp,
        ))

    return anomaly.to_dict() | {"alert_triggered": triggered}


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


