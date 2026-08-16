import os
import json
from typing import List
from openai import OpenAI
from app.models.schemas import SystemTelemetry, IncidentReport, SeverityLevel, RunbookSource
from app.engine.anomaly_detector import AnomalyDetector
from app.rag.runbook_search import RunbookSearchEngine

class IncidentSynthesizer:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.search_engine = RunbookSearchEngine()
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

    def analyze_telemetry(self, telemetry: SystemTelemetry) -> IncidentReport:
        # 1. Evaluate metrics against threshold rules
        detection = self.detector.evaluate(telemetry)
        
        # Healthy system branch
        if not detection["has_anomalies"]:
            return IncidentReport(
                incident_title="System Health Normal",
                severity=SeverityLevel.LOW,
                likely_cause="All system metrics and services are operating within normal operational thresholds.",
                recommended_actions=["Continue routine telemetry monitoring."],
                escalation_required=False,
                escalation_criteria=None,
                sources_consulted=[]
            )

        # 2. Retrieve relevant runbooks via vector search
        query_string = " ".join(detection["anomalies"])
        sources: List[RunbookSource] = self.search_engine.search(query_string, top_k=2)

        # 3. Use OpenAI Structured Outputs if API Key is available
        if self.client:
            try:
                runbook_context = "\n\n".join([
                    f"--- Runbook: {s.title} ---\n{s.file_path}" for s in sources
                ])

                prompt = f"""
                Analyze the following active system anomalies and generate an SRE incident report using the provided runbook context.

                Active Anomalies:
                {json.dumps(detection['anomalies'], indent=2)}

                Matched Runbooks:
                {runbook_context if runbook_context else "No matching runbooks found."}
                """

                completion = self.client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a Senior SRE Incident Commander synthesizing telemetry anomalies and runbook knowledge."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    response_format=IncidentReport,
                    temperature=0.2
                )
                
                report = completion.choices[0].message.parsed
                report.sources_consulted = sources
                return report
            except Exception:
                # Fall back to deterministic rules if API call fails
                pass

        # 4. Deterministic Fallback Logic
        return self._rule_based_synthesis(telemetry, detection, sources)

    def _rule_based_synthesis(
        self, telemetry: SystemTelemetry, detection: dict, sources: List[RunbookSource]
    ) -> IncidentReport:
        severity = SeverityLevel.MEDIUM
        if telemetry.disk_percent >= 95.0 or telemetry.cpu_percent >= 95.0:
            severity = SeverityLevel.HIGH
        
        down_services = [svc for svc, status in telemetry.services.items() if status.upper() in ["DOWN", "FAILED"]]
        if down_services and telemetry.disk_percent >= 90.0:
            severity = SeverityLevel.CRITICAL

        title = f"Incident: Infrastructure Degradation ({', '.join(detection['anomalies'][:2])})"
        cause = f"Detected {detection['anomaly_count']} system anomaly/anomalies: {'; '.join(detection['anomalies'])}."

        actions = [
            "Inspect system and application logs under /var/log for critical errors.",
            "Verify process states and resource consumption using system diagnostic tools.",
        ]
        
        if telemetry.disk_percent >= 90.0:
            actions.append("Identify and remove/rotate large log files to free up disk capacity.")
            
        for svc in down_services:
            actions.append(f"Attempt service restart for: {svc}")

        escalation_required = severity in [SeverityLevel.HIGH, SeverityLevel.CRITICAL]
        escalation_criteria = (
            "Escalate to On-Call Infrastructure Team if service recovery fails after automated actions or disk usage remains >95%."
            if escalation_required else None
        )

        return IncidentReport(
            incident_title=title,
            severity=severity,
            likely_cause=cause,
            recommended_actions=actions,
            escalation_required=escalation_required,
            escalation_criteria=escalation_criteria,
            sources_consulted=sources
        )