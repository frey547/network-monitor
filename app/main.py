import time
import threading
import numpy as np
from fastapi import FastAPI
import uvicorn

from app.detector import AnomalyDetector, AnomalyResult
from app.alert_manager import AlertManager

from prometheus_client import Counter, generate_latest
from fastapi.responses import Response

app = FastAPI()

REQUEST_COUNT = Counter("request_count", "Total API requests")

detector = AnomalyDetector()
alert_mgr = AlertManager(limit_per_minute=2, window_seconds=5)
metrics_state = {"cpu": 0, "memory": 0}


# 模拟指标采集线程

def simulate_metrics():
    while True:
        # 模拟 CPU 和内存
        metrics_state["cpu"] = np.random.normal(30, 5)
        metrics_state["memory"] = np.random.normal(60, 10)

        # detector 检测
        for metric, value in metrics_state.items():
            detector.add(metric, value)
            result = detector.detect(metric, value)
            if result.is_anomaly:
                triggered = alert_mgr.add_alert(metric, result)
                if triggered:
                    print(f"[ALERT] {metric} abnormal! z={result.z_score:.2f}")

        time.sleep(2)  # 每 2 秒采集一次


# API 接口

@app.get("/metrics/app")
def get_metrics():
    return {
        metric: {
            "value": val,
            "z_score": detector.detect(metric, val).z_score,
            "is_anomaly": detector.detect(metric, val).is_anomaly
        }
        for metric, val in metrics_state.items()
    }

@app.get("/alerts")
def get_alerts():
    return alert_mgr.get_alerts()

@app.get("/simulate")
def simulate_anomaly(metric: str = "cpu", value: float = 100):
    """手动模拟异常"""
    detector.add(metric, value)
    result = detector.detect(metric, value)
    triggered = alert_mgr.add_alert(metric, result)
    return {
        "metric": metric,
        "value": value,
        "z_score": result.z_score,
        "is_anomaly": result.is_anomaly,
        "alert_triggered": triggered
    }

@app.get("/health")
def health():
    return {"status": "ok"}


@app.middleware("http")
async def count_requests(request, call_next):
    REQUEST_COUNT.inc()
    response = await call_next(request)
    return response

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

# 启动线程

threading.Thread(target=simulate_metrics, daemon=True).start()

