from unittest.mock import MagicMock, patch

import pytest

from app.ai.analyzer import AIAnalyzer
from app.models.alert import AIResult, AlertInput, AlertType, RuleResult, Severity


@pytest.fixture
def mock_openai_response():
    choice = MagicMock()
    choice.message.content = '{"summary":"CPU spike from cron job","risk_analysis":"medium","additional_suggestions":["check crontab"]}'
    resp = MagicMock()
    resp.choices = [choice]
    return resp


@pytest.fixture
def analyzer_with_mock(mock_openai_response):
    with patch("app.ai.analyzer.AI_ENABLED", True):
        analyzer = AIAnalyzer.__new__(AIAnalyzer)
        analyzer.client = MagicMock()
        analyzer.client.chat.completions.create.return_value = mock_openai_response
        yield analyzer


class TestShouldEnhance:
    def test_unknown_triggers_ai(self):
        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            rule = RuleResult(
                alert_type=AlertType.UNKNOWN,
                severity=Severity.WARNING,
                reason="unknown",
                suggestions=[],
                commands=[],
            )
            assert analyzer.should_enhance(rule) is True

    def test_critical_triggers_ai(self):
        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            rule = RuleResult(
                alert_type=AlertType.CPU,
                severity=Severity.CRITICAL,
                reason="cpu high",
                suggestions=[],
                commands=[],
            )
            assert analyzer.should_enhance(rule) is True

    def test_warning_skips_ai(self):
        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            rule = RuleResult(
                alert_type=AlertType.CPU,
                severity=Severity.WARNING,
                reason="cpu moderate",
                suggestions=[],
                commands=[],
            )
            assert analyzer.should_enhance(rule) is False

    def test_disabled_skips_ai(self):
        with patch("app.ai.analyzer.AI_ENABLED", False):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            rule = RuleResult(
                alert_type=AlertType.UNKNOWN,
                severity=Severity.CRITICAL,
                reason="unknown",
                suggestions=[],
                commands=[],
            )
            assert analyzer.should_enhance(rule) is False


class TestEnhance:
    def test_parses_valid_json(self, analyzer_with_mock):
        alert = AlertInput(alertname="HighCPU", instance="node-1", value=96)
        rule = RuleResult(
            alert_type=AlertType.CPU,
            severity=Severity.CRITICAL,
            reason="cpu high",
            suggestions=["check top"],
            commands=["top"],
        )
        result = analyzer_with_mock.enhance(alert, rule)
        assert isinstance(result, AIResult)
        assert result.summary == "CPU spike from cron job"
        assert "check crontab" in result.additional_suggestions

    def test_handles_malformed_json(self):
        choice = MagicMock()
        choice.message.content = "this is not json at all"
        resp = MagicMock()
        resp.choices = [choice]

        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            analyzer.client.chat.completions.create.return_value = resp

            alert = AlertInput(alertname="HighCPU", value=96)
            rule = RuleResult(
                alert_type=AlertType.CPU,
                severity=Severity.CRITICAL,
                reason="x",
                suggestions=[],
                commands=[],
            )
            result = analyzer.enhance(alert, rule)
            assert isinstance(result, AIResult)
            assert result.summary == "this is not json at all"

    def test_handles_api_exception(self):
        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            analyzer.client.chat.completions.create.side_effect = Exception("timeout")

            alert = AlertInput(alertname="HighCPU", value=96)
            rule = RuleResult(
                alert_type=AlertType.CPU,
                severity=Severity.CRITICAL,
                reason="x",
                suggestions=[],
                commands=[],
            )
            result = analyzer.enhance(alert, rule)
            assert result is None

    def test_strips_markdown_code_block(self):
        choice = MagicMock()
        choice.message.content = '```json\n{"summary":"wrapped","risk_analysis":"","additional_suggestions":[]}\n```'
        resp = MagicMock()
        resp.choices = [choice]

        with patch("app.ai.analyzer.AI_ENABLED", True):
            analyzer = AIAnalyzer.__new__(AIAnalyzer)
            analyzer.client = MagicMock()
            analyzer.client.chat.completions.create.return_value = resp

            alert = AlertInput(alertname="X", value=96)
            rule = RuleResult(
                alert_type=AlertType.CPU,
                severity=Severity.CRITICAL,
                reason="x",
                suggestions=[],
                commands=[],
            )
            result = analyzer.enhance(alert, rule)
            assert result.summary == "wrapped"
