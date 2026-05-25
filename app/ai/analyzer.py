import json
import logging

from openai import OpenAI

from app.ai.client import create_ai_client
from app.ai.prompts import (
    SYSTEM_PROMPT,
    build_enhancement_prompt,
    build_unknown_alert_prompt,
)
from app.config import AI_ENABLED, AI_MAX_TOKENS, AI_TEMPERATURE, DEEPSEEK_MODEL
from app.models.alert import AIResult, AlertInput, AlertType, RuleResult

logger = logging.getLogger(__name__)


class AIAnalyzer:
    def __init__(self) -> None:
        self.client: OpenAI | None = None
        if AI_ENABLED:
            try:
                self.client = create_ai_client()
            except Exception as exc:
                logger.warning("AI client init failed: %s", exc)

    def should_enhance(self, rule_result: RuleResult) -> bool:
        if not AI_ENABLED or self.client is None:
            return False
        if rule_result.alert_type == AlertType.UNKNOWN:
            return True
        if rule_result.severity.value == "critical":
            return True
        return False

    def enhance(self, alert: AlertInput, rule_result: RuleResult) -> AIResult | None:
        if self.client is None:
            return None

        if rule_result.alert_type == AlertType.UNKNOWN:
            user_prompt = build_unknown_alert_prompt(alert)
        else:
            user_prompt = build_enhancement_prompt(alert, rule_result)

        try:
            response = self.client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=AI_MAX_TOKENS,
                temperature=AI_TEMPERATURE,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content or ""
            return self._parse(content.strip())
        except Exception as exc:
            logger.error("AI enhancement failed: %s", exc)
            return None

    @staticmethod
    def _parse(content: str) -> AIResult:
        if content.startswith("```"):
            lines = content.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            content = "\n".join(lines[1:end])

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return AIResult(summary=content[:100])

        return AIResult(
            summary=data.get("summary", ""),
            risk_analysis=data.get("risk_analysis", ""),
            additional_suggestions=data.get("additional_suggestions", []),
        )
