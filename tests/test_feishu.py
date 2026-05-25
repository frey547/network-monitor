from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.alert import AlertType, AnalysisResult, Severity
from app.notify.feishu import FeishuNotifier


@pytest.fixture
def notifier():
    return FeishuNotifier(webhook_url="https://example.com/hook/test")


@pytest.fixture
def sample_result():
    return AnalysisResult(
        alert_type=AlertType.CPU,
        severity=Severity.CRITICAL,
        reason="CPU负载过高",
        suggestions=["检查高CPU进程", "考虑扩容"],
        commands=["top -bn1 | head -20", "ps aux --sort=-%cpu | head -10"],
        runbook="1. top\n2. kill",
        source="rule",
    )


class TestBuildCard:
    def test_card_structure(self, notifier, sample_result):
        card = notifier._build_card(sample_result, "HighCPU", "node-1")
        assert card["msg_type"] == "interactive"
        assert card["card"]["header"]["template"] == "red"
        assert "CRITICAL" in card["card"]["header"]["title"]["content"]

    def test_card_has_all_sections(self, notifier, sample_result):
        card = notifier._build_card(sample_result, "HighCPU", "node-1")
        elements = card["card"]["elements"]
        texts = []
        for el in elements:
            if "text" in el and "content" in el.get("text", {}):
                texts.append(el["text"]["content"])
        combined = "\n".join(texts)
        assert "原因分析" in combined
        assert "处理建议" in combined
        assert "排查命令" in combined

    def test_card_with_ai_summary(self, notifier):
        result = AnalysisResult(
            alert_type=AlertType.CPU,
            severity=Severity.WARNING,
            reason="test",
            suggestions=["s1"],
            commands=["cmd1"],
            ai_summary="AI says check cron",
            ai_suggestions=["look at crontab"],
            source="rule+ai",
        )
        card = notifier._build_card(result, "Test", "inst")
        combined = str(card)
        assert "AI 补充分析" in combined
        assert "AI says check cron" in combined

    def test_card_severity_colors(self, notifier):
        for sev, expected_color in [
            (Severity.CRITICAL, "red"),
            (Severity.WARNING, "orange"),
            (Severity.INFO, "green"),
        ]:
            result = AnalysisResult(
                alert_type=AlertType.CPU,
                severity=sev,
                reason="x",
                suggestions=[],
                commands=[],
            )
            card = notifier._build_card(result, "X", "")
            assert card["card"]["header"]["template"] == expected_color


class TestSend:
    @pytest.mark.asyncio
    async def test_send_success(self, notifier, sample_result):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '{"code": 0, "msg": "success"}'
        mock_resp.json.return_value = {"code": 0, "msg": "success"}

        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_resp
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.notify.feishu.httpx.AsyncClient", return_value=mock_client_instance):
            ok = await notifier.send(sample_result, alert_name="HighCPU", instance="node-1")
        assert ok is True
        mock_client_instance.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_no_url_returns_false(self, sample_result):
        notifier = FeishuNotifier(webhook_url="")
        ok = await notifier.send(sample_result)
        assert ok is False

    @pytest.mark.asyncio
    async def test_send_handles_http_error(self, notifier, sample_result):
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = Exception("connection refused")
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=False)

        with patch("app.notify.feishu.httpx.AsyncClient", return_value=mock_client_instance):
            ok = await notifier.send(sample_result, alert_name="X", instance="Y")
        assert ok is False
