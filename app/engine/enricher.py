from app.knowledge.history import AlertHistory
from app.models.alert import AIResult, AlertInput, AnalysisResult, RuleResult


class AlertEnricher:
    def __init__(self, history: AlertHistory):
        self.history = history

    def enrich(
        self,
        alert: AlertInput,
        rule_result: RuleResult,
        ai_result: AIResult | None = None,
    ) -> AnalysisResult:
        self.history.record(alert)

        suggestions = list(rule_result.suggestions)
        recent_count = self.history.recent_count(alert.alertname, window_minutes=30)
        if recent_count > 3:
            suggestions.insert(
                0,
                f"注意: 过去30分钟内该告警已触发{recent_count}次，建议排查持续性根因",
            )

        return AnalysisResult(
            alert_type=rule_result.alert_type,
            severity=rule_result.severity,
            reason=rule_result.reason,
            suggestions=suggestions,
            commands=rule_result.commands,
            runbook=rule_result.runbook,
            ai_summary=ai_result.summary if ai_result else "",
            ai_suggestions=ai_result.additional_suggestions if ai_result else [],
            source="rule+ai" if ai_result else "rule",
        )
