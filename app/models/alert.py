from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Optional

from pydantic import BaseModel, BeforeValidator, Field


class AlertType(str, Enum):
    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    POD_CRASH = "pod_crash"
    NETWORK = "network"
    UNKNOWN = "unknown"


class Severity(str, Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


def _coerce_numeric(v: Any) -> Optional[float]:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, str):
        cleaned = v.strip().rstrip("%")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


CoercedFloat = Annotated[Optional[float], BeforeValidator(_coerce_numeric)]


class AlertInput(BaseModel):
    alertname: str
    status: str = "firing"
    instance: str = ""
    description: str = ""
    value: CoercedFloat = None
    labels: dict = Field(default_factory=dict)
    annotations: dict = Field(default_factory=dict)


class RuleResult(BaseModel):
    alert_type: AlertType
    severity: Severity
    reason: str
    suggestions: list[str]
    commands: list[str]
    runbook: str = ""
    matched_rule: str = ""


class AIResult(BaseModel):
    summary: str = ""
    risk_analysis: str = ""
    additional_suggestions: list[str] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    alert_type: AlertType
    severity: Severity
    reason: str
    suggestions: list[str]
    commands: list[str]
    runbook: str = ""
    ai_summary: str = ""
    ai_suggestions: list[str] = Field(default_factory=list)
    source: str = "rule"
