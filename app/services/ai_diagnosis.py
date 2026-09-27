"""AI-enhanced diagnosis service.

When an AI provider (OpenAI) is configured, the diagnosis engine can use
LLM reasoning over collected evidence to enhance the deterministic diagnosis.
The AI never invents evidence — it only reasons over what was collected.
"""

import json
import logging
from typing import Any

from app.config.settings import settings
from app.database.models import Incident
from app.database.repositories import get_incident_evidence
from app.monitoring.metrics import AI_DIAGNOSES

logger = logging.getLogger(__name__)


class AIDiagnosisService:
    """Enhances deterministic diagnosis with LLM reasoning.

    The AI is ONLY used to reason over collected evidence.
    It never invents evidence or root causes.
    """

    def __init__(self) -> None:
        self._client = None
        if settings.OPENAI_API_KEY and settings.AI_ENABLED:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
                logger.info("AI diagnosis service initialized")
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client: %s", e)

    def is_available(self) -> bool:
        """Check if AI enhancement is available."""
        return self._client is not None

    def enhance_diagnosis(self, incident: Incident) -> dict[str, Any] | None:
        """Enhance diagnosis using LLM reasoning over collected evidence.

        Returns None if AI is not available or enhancement fails.
        """
        if not self.is_available():
            return None

        try:
            # Gather collected evidence
            from sqlalchemy.orm import Session

            # We need a DB session to get evidence
            # This is passed via the incident's evidence relationship
            evidence_items = []
            for ev in incident.evidence:
                evidence_items.append({
                    "type": ev.evidence_type,
                    "source": ev.source,
                    "content": ev.content[:500],  # Truncate for token limits
                })

            if not evidence_items:
                logger.warning("No evidence available for AI diagnosis")
                return None

            # Build prompt — AI only reasons over collected evidence
            evidence_json = json.dumps(evidence_items, indent=2)

            prompt = f"""You are a Senior SRE Incident Commander. Analyze the following collected evidence
and provide a structured diagnosis. Do NOT invent any evidence — only reason over what is provided.

Incident: {incident.title}
Severity: {incident.severity}
Environment: {incident.environment}
Symptoms: {incident.symptoms or 'Not provided'}

Collected Evidence:
{evidence_json}

Provide your analysis in this exact JSON format:
{{
    "probable_cause": "description of the most likely root cause",
    "confidence": 0.0 to 1.0,
    "alternative_causes": ["cause1", "cause2"],
    "recommended_action": "specific remediation action",
    "reasoning": "brief explanation of your reasoning"
}}

Rules:
- Base your diagnosis ONLY on the provided evidence
- If evidence is insufficient, lower your confidence
- Suggest concrete, actionable remediation steps
- Consider deployment correlations, resource exhaustion, and dependency failures
"""

            response = self._client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a Senior SRE Incident Commander using "
                            "infrastructure evidence to diagnose incidents."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=1000,
            )

            content = response.choices[0].message.content

            # Parse JSON response
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0]

            result = json.loads(content)

            AI_DIAGNOSES.inc()

            logger.info(
                "AI diagnosis complete for incident %s: confidence=%.2f",
                incident.incident_key,
                result.get("confidence", 0),
            )

            return result

        except Exception as e:
            logger.error("AI diagnosis failed: %s", e)
            return None
