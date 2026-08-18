import json
import os
from typing import List

from openai import OpenAI

from app.engine.anomaly_detector import AnomalyDetector
from app.models.schemas import (
    AnalysisMethod,
    IncidentReport,
    RunbookSource,
    SeverityLevel,
    SystemTelemetry,
)
from app.rag.runbook_search import RunbookSearchEngine


class IncidentSynthesizer:
    def __init__(self):
        self.detector = AnomalyDetector()
        self.search_engine = RunbookSearchEngine()

        api_key = os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=api_key) if api_key else None

    def analyze_telemetry(self, telemetry: SystemTelemetry) -> IncidentReport:
        # 1. Evaluate telemetry against threshold rules
        detection = self.detector.evaluate(telemetry)

        # Healthy system branch
        if not detection["has_anomalies"]:
            return IncidentReport(
                incident_title="System Health Normal",
                severity=SeverityLevel.LOW,
                likely_cause=(
                    "All system metrics and services are operating "
                    "within normal operational thresholds."
                ),
                recommended_actions=["Continue routine telemetry monitoring."],
                escalation_required=False,
                escalation_criteria=None,
                sources_consulted=[],
                analysis_method=AnalysisMethod.RULE_BASED,
            )

        # 2. Retrieve relevant runbooks using semantic search
        query_string = " ".join(detection["anomalies"])

        runbook_matches = self.search_engine.search_with_content(
            query_string,
            top_k=4,
        )

        sources: List[RunbookSource] = [
            RunbookSource(
                title=match["title"],
                file_path=match["file_path"],
                relevance_score=match["relevance_score"],
            )
            for match in runbook_matches
        ]

        # 3. Optional OpenAI synthesis
        if self.client:
            try:
                runbook_context = "\n\n".join(
                    [
                        f"--- Runbook: {match['title']} ---\n" f"{match['content']}"
                        for match in runbook_matches
                    ]
                )

                prompt = f"""
Analyze the following infrastructure anomalies and generate
a structured SRE incident report.

Active anomalies:
{json.dumps(detection["anomalies"], indent=2)}

Retrieved runbook knowledge:
{runbook_context if runbook_context else "No matching runbook content was found."}

Use the retrieved runbook knowledge when generating
recommended actions and escalation criteria.
Do not invent procedures that contradict the runbook.
"""

                completion = self.client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a Senior SRE Incident Commander "
                                "using infrastructure telemetry and "
                                "retrieved runbook knowledge."
                            ),
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                    response_format=IncidentReport,
                    temperature=0.2,
                )

                report = completion.choices[0].message.parsed

                if report is not None:
                    report.sources_consulted = sources
                    report.analysis_method = AnalysisMethod.OPENAI
                    return report

            except Exception:
                # OpenAI is optional. Use local RAG synthesis if unavailable.
                pass

        # 4. Local RAG-based synthesis
        return self._rule_based_synthesis(
            telemetry,
            detection,
            sources,
            runbook_matches,
        )

    def _rule_based_synthesis(
        self,
        telemetry: SystemTelemetry,
        detection: dict,
        sources: List[RunbookSource],
        runbook_matches: list,
    ) -> IncidentReport:

        severity = SeverityLevel.MEDIUM

        if telemetry.disk_percent >= 95.0 or telemetry.cpu_percent >= 95.0:
            severity = SeverityLevel.HIGH

        down_services = [
            service
            for service, status in telemetry.services.items()
            if status.upper() in ["DOWN", "FAILED"]
        ]

        if down_services and telemetry.disk_percent >= 90.0:
            severity = SeverityLevel.CRITICAL

        title = (
            "Incident: Infrastructure Degradation "
            f"({', '.join(detection['anomalies'][:2])})"
        )

        cause = (
            f"Detected {detection['anomaly_count']} "
            f"system anomaly/anomalies: "
            f"{'; '.join(detection['anomalies'])}."
        )

        # Start with actions derived from the retrieved runbooks.
        actions = []

        runbook_titles = {match["title"] for match in runbook_matches}

        if "disk_and_webserver.md" in runbook_titles:
            actions.extend(
                [
                    "Inspect log directories under /var/log for oversized log files.",
                    "Clear temporary files under /tmp and rotate active logs using logrotate.",
                    "Verify available disk space using df -h.",
                ]
            )

            if down_services:
                services = ", ".join(down_services)
                actions.append(
                    f"Once disk usage drops below 90%, "
                    f"restart the affected web service: {services}."
                )

        if "service_outage.md" in runbook_titles and down_services:
            services = ", ".join(down_services)

            actions.extend(
                [
                    f"Check the status of the affected service: {services}.",
                    "Inspect recent application and system logs.",
                    "Re-run the health check endpoint after remediation.",
                ]
            )

        if "high_cpu.md" in runbook_titles:
            actions.append(
                "Identify high CPU processes and investigate "
                "resource-intensive workloads."
            )

        if "memory_pressure.md" in runbook_titles:
            actions.append(
                "Identify memory-intensive processes and check "
                "for memory leaks or OOM events."
            )

        # Fallback actions if no relevant runbook was retrieved.
        if not actions:
            actions = [
                "Inspect system and application logs for critical errors.",
                "Verify process states and resource consumption "
                "using system diagnostic tools.",
            ]

        # Prefer escalation criteria from the retrieved runbooks.
        escalation_criteria = None

        if "disk_and_webserver.md" in runbook_titles:
            escalation_criteria = (
                "Escalate to Infrastructure/Storage Team if "
                "disk usage remains >95% after log cleanup "
                "or if unpartitioned disk space is exhausted."
            )

        elif "service_outage.md" in runbook_titles and down_services:
            escalation_criteria = (
                "Escalate to the On-Call Infrastructure or Application "
                "Team if the service does not recover after restart "
                "or multiple services are affected."
            )

        elif "memory_pressure.md" in runbook_titles:
            escalation_criteria = (
                "Escalate to the Application or Infrastructure Team if "
                "memory usage remains above 95%, the system triggers "
                "OOM events, or services repeatedly crash."
            )

        elif "high_cpu.md" in runbook_titles:
            escalation_criteria = (
                "Escalate to the Infrastructure or Application Team if "
                "CPU usage remains above 95% after remediation "
                "or the service becomes unavailable."
            )

        escalation_required = severity in [
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        ]

        if escalation_required and not escalation_criteria:
            escalation_criteria = (
                "Escalate to On-Call Infrastructure Team if "
                "service recovery fails after automated actions "
                "or disk usage remains >95%."
            )

        return IncidentReport(
            incident_title=title,
            severity=severity,
            likely_cause=cause,
            recommended_actions=actions,
            escalation_required=escalation_required,
            escalation_criteria=escalation_criteria,
            sources_consulted=sources,
            analysis_method=AnalysisMethod.RULE_BASED,
        )
