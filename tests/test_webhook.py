from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.ai.analyzer import AIAnalyzer
from app.api.webhook import router as webhook_router
from app.engine.enricher import AlertEnricher
from app.engine.rule_engine import RuleEngine
from app.knowledge.history import AlertHistory
from app.models.alert import AlertType, Severity
from app.notify.feishu import FeishuNotifier


def _create_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(webhook_router)

    app.state.rule_engine = RuleEngine()
    ai = AIAnalyzer.__new__(AIAnalyzer)
    ai.client = None
    app.state.ai_analyzer = ai
    app.state.enricher = AlertEnricher(AlertHistory())
    app.state.feishu = FeishuNotifier(webhook_url="")
    return app


@pytest.fixture
def client():
    return TestClient(_create_test_app(), raise_server_exceptions=True)


class TestWebhookEndpoint:
    def test_empty_alerts(self, client):
        resp = client.post("/webhook/alert", json={"alerts": []})
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_cpu_alert(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "HighCPUUsage",
                        "instance": "node-1",
                        "severity": "critical",
                    },
                    "annotations": {
                        "description": "CPU over 95%",
                        "value": "96",
                    },
                }
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        result = body["results"][0]
        assert result["alert_type"] == "cpu"
        assert result["severity"] == "critical"
        assert result["source"] == "rule"
        assert len(result["commands"]) > 0

    def test_multiple_alerts(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighCPUUsage", "instance": "n1"},
                    "annotations": {"value": "90"},
                },
                {
                    "status": "firing",
                    "labels": {"alertname": "DiskSpaceLow", "instance": "n2"},
                    "annotations": {"value": "96"},
                },
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        body = resp.json()
        assert body["count"] == 2
        types = {r["alert_type"] for r in body["results"]}
        assert types == {"cpu", "disk"}

    def test_unknown_alert(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "SomethingWeird"},
                    "annotations": {},
                }
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        body = resp.json()
        assert body["results"][0]["alert_type"] == "unknown"

    def test_pod_crash_alert(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {
                        "alertname": "KubePodCrashLooping",
                        "instance": "app-pod-xyz",
                    },
                    "annotations": {"value": "7"},
                }
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        result = resp.json()["results"][0]
        assert result["alert_type"] == "pod_crash"
        assert result["severity"] == "critical"

    def test_network_alert(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighNetworkLatency", "instance": "gw-1"},
                    "annotations": {"value": "1200"},
                }
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        result = resp.json()["results"][0]
        assert result["alert_type"] == "network"
        assert result["severity"] == "critical"

    def test_value_percent_string_coercion(self, client):
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighMemoryUsage"},
                    "annotations": {"value": "92%"},
                }
            ]
        }
        resp = client.post("/webhook/alert", json=payload)
        result = resp.json()["results"][0]
        assert result["alert_type"] == "memory"
        assert result["severity"] == "warning"


class TestWebhookFeishuIntegration:
    def test_feishu_called_on_alert(self):
        app = _create_test_app()
        mock_feishu = FeishuNotifier(webhook_url="https://fake.feishu/hook")
        mock_feishu.send = AsyncMock(return_value=True)
        app.state.feishu = mock_feishu

        tc = TestClient(app, raise_server_exceptions=True)
        payload = {
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighCPUUsage"},
                    "annotations": {"value": "95"},
                }
            ]
        }
        resp = tc.post("/webhook/alert", json=payload)
        assert resp.status_code == 200
        mock_feishu.send.assert_called_once()
