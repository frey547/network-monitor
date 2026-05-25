import pytest

from app.engine.rule_engine import RuleEngine
from app.knowledge.history import AlertHistory
from app.engine.enricher import AlertEnricher
from app.models.alert import AlertInput, AlertType, Severity


@pytest.fixture
def engine():
    return RuleEngine()


@pytest.fixture
def enricher():
    return AlertEnricher(AlertHistory())


# --------------- classifier ---------------

class TestClassifier:
    @pytest.mark.parametrize(
        "alertname, expected_type",
        [
            ("HighCPUUsage", AlertType.CPU),
            ("node_cpu_high", AlertType.CPU),
            ("HighMemoryUsage", AlertType.MEMORY),
            ("OOMKilled", AlertType.MEMORY),
            ("DiskSpaceLow", AlertType.DISK),
            ("FilesystemFull", AlertType.DISK),
            ("KubePodCrashLooping", AlertType.POD_CRASH),
            ("CrashLoopBackOff", AlertType.POD_CRASH),
            ("NetworkLatencyHigh", AlertType.NETWORK),
            ("DNSResolutionFailure", AlertType.NETWORK),
            ("SomeRandomAlert", AlertType.UNKNOWN),
        ],
    )
    def test_classification(self, engine, alertname, expected_type):
        alert = AlertInput(alertname=alertname)
        result = engine.evaluate(alert)
        assert result.alert_type == expected_type


# --------------- severity ---------------

class TestSeverity:
    def test_cpu_critical(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", value=96)
        assert engine.evaluate(alert).severity == Severity.CRITICAL

    def test_cpu_warning(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", value=85)
        assert engine.evaluate(alert).severity == Severity.WARNING

    def test_cpu_info(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", value=50)
        assert engine.evaluate(alert).severity == Severity.INFO

    def test_none_value_defaults_warning(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", value=None)
        assert engine.evaluate(alert).severity == Severity.WARNING

    def test_string_percent_value_coerced(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", value="95%")
        result = engine.evaluate(alert)
        assert result.severity == Severity.CRITICAL
        assert result.alert_type == AlertType.CPU


# --------------- rule result structure ---------------

class TestRuleResult:
    def test_known_alert_has_commands(self, engine):
        alert = AlertInput(alertname="HighCPUUsage", instance="node-1", value=95)
        result = engine.evaluate(alert)
        assert len(result.commands) > 0
        assert len(result.suggestions) > 0
        assert result.runbook != ""
        assert result.matched_rule == "cpu"

    def test_unknown_alert(self, engine):
        alert = AlertInput(alertname="CustomMetricHigh", value=42)
        result = engine.evaluate(alert)
        assert result.alert_type == AlertType.UNKNOWN
        assert result.matched_rule == ""

    def test_all_alert_types_have_rules(self, engine):
        names = {
            AlertType.CPU: "HighCPU",
            AlertType.MEMORY: "HighMemory",
            AlertType.DISK: "DiskFull",
            AlertType.POD_CRASH: "PodCrashLoopBackOff",
            AlertType.NETWORK: "NetworkLatency",
        }
        for expected_type, alertname in names.items():
            result = engine.evaluate(AlertInput(alertname=alertname))
            assert result.alert_type == expected_type, f"{alertname} should map to {expected_type}"


# --------------- enricher ---------------

class TestEnricher:
    def test_enricher_adds_history_warning(self, engine, enricher):
        alert = AlertInput(alertname="HighCPUUsage", value=90)
        rule_result = engine.evaluate(alert)
        for _ in range(5):
            enricher.enrich(alert, rule_result)
        analysis = enricher.enrich(alert, rule_result)
        assert any("过去30分钟" in s for s in analysis.suggestions)

    def test_enricher_source_rule_only(self, engine, enricher):
        alert = AlertInput(alertname="HighCPUUsage", value=90)
        rule_result = engine.evaluate(alert)
        analysis = enricher.enrich(alert, rule_result)
        assert analysis.source == "rule"
        assert analysis.ai_summary == ""

    def test_enricher_source_with_ai(self, engine, enricher):
        from app.models.alert import AIResult
        alert = AlertInput(alertname="HighCPUUsage", value=90)
        rule_result = engine.evaluate(alert)
        ai_result = AIResult(summary="test summary", additional_suggestions=["extra tip"])
        analysis = enricher.enrich(alert, rule_result, ai_result)
        assert analysis.source == "rule+ai"
        assert analysis.ai_summary == "test summary"
        assert "extra tip" in analysis.ai_suggestions
