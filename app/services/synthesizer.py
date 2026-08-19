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
        detection = self.detector.evaluate(telemetry)

        if not detection["has_anomalies"]:
            return self._healthy_report()

        query_string = " ".join(detection["anomalies"])

        runbook_matches = self.search_engine.search_with_content(
            query_string,
            top_k=4,
        )

        sources = self._build_sources(runbook_matches)

        if self.client:
            report = self._openai_synthesis(
                detection=detection,
                runbook_matches=runbook_matches,
                sources=sources,
            )

            if report is not None:
                return report

        return self._rule_based_synthesis(
            telemetry=telemetry,
            detection=detection,
            sources=sources,
            runbook_matches=runbook_matches,
        )

    @staticmethod
    def _healthy_report() -> IncidentReport:
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

    @staticmethod
    def _build_sources(
        runbook_matches: list,
    ) -> List[RunbookSource]:
        return [
            RunbookSource(
                title=match["title"],
                file_path=match["file_path"],
                relevance_score=match["relevance_score"],
            )
            for match in runbook_matches
        ]

    def _openai_synthesis(
        self,
        detection: dict,
        runbook_matches: list,
        sources: List[RunbookSource],
    ) -> IncidentReport | None:
        try:
            runbook_context = "\n\n".join(
                f"--- Runbook: {match['title']} ---\n{match['content']}"
                for match in runbook_matches
            )

            if not runbook_context:
                runbook_context = "No matching runbook content was found."

            prompt = f"""
Analyze the following infrastructure anomalies and generate
a structured SRE incident report.

Active anomalies:
{json.dumps(detection["anomalies"], indent=2)}

Retrieved runbook knowledge:
{runbook_context}

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

            if report is None:
                return None

            report.sources_consulted = sources
            report.analysis_method = AnalysisMethod.OPENAI

            return report

        except Exception:
            # OpenAI is optional. Fall back to local synthesis.
            return None

    @staticmethod
    def _determine_severity(
        telemetry: SystemTelemetry,
        down_services: List[str],
    ) -> SeverityLevel:
        if down_services and telemetry.disk_percent >= 90.0:
            return SeverityLevel.CRITICAL

        if telemetry.disk_percent >= 95.0 or telemetry.cpu_percent >= 95.0:
            return SeverityLevel.HIGH

        return SeverityLevel.MEDIUM

    @staticmethod
    def _get_down_services(
        telemetry: SystemTelemetry,
    ) -> List[str]:
        return [
            service
            for service, service_status in telemetry.services.items()
            if service_status.upper() in {"DOWN", "FAILED"}
        ]

    @staticmethod
    def _build_actions(
        runbook_titles: set,
        down_services: List[str],
    ) -> List[str]:
        actions = []

        if "disk_and_webserver.md" in runbook_titles:
            actions.extend(
                [
                    (
                        "Inspect log directories under /var/log "
                        "for oversized log files."
                    ),
                    (
                        "Clear temporary files under /tmp and "
                        "rotate active logs using logrotate."
                    ),
                    "Verify available disk space using df -h.",
                ]
            )

            if down_services:
                services = ", ".join(down_services)
                actions.append(
                    "Once disk usage drops below 90%, "
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

        if not actions:
            actions = [
                "Inspect system and application logs for critical errors.",
                (
                    "Verify process states and resource consumption "
                    "using system diagnostic tools."
                ),
            ]

        return actions

    @staticmethod
    def _build_escalation_criteria(
        runbook_titles: set,
        down_services: List[str],
        escalation_required: bool,
    ) -> str | None:
        if "disk_and_webserver.md" in runbook_titles:
            return (
                "Escalate to Infrastructure/Storage Team if "
                "disk usage remains >95% after log cleanup "
                "or if unpartitioned disk space is exhausted."
            )

        if "service_outage.md" in runbook_titles and down_services:
            return (
                "Escalate to the On-Call Infrastructure or Application "
                "Team if the service does not recover after restart "
                "or multiple services are affected."
            )

        if "memory_pressure.md" in runbook_titles:
            return (
                "Escalate to the Application or Infrastructure Team if "
                "memory usage remains above 95%, the system triggers "
                "OOM events, or services repeatedly crash."
            )

        if "high_cpu.md" in runbook_titles:
            return (
                "Escalate to the Infrastructure or Application Team if "
                "CPU usage remains above 95% after remediation "
                "or the service becomes unavailable."
            )

        if escalation_required:
            return (
                "Escalate to On-Call Infrastructure Team if "
                "service recovery fails after automated actions "
                "or disk usage remains >95%."
            )

        return None

    def _rule_based_synthesis(
        self,
        telemetry: SystemTelemetry,
        detection: dict,
        sources: List[RunbookSource],
        runbook_matches: list,
    ) -> IncidentReport:
        down_services = self._get_down_services(telemetry)

        severity = self._determine_severity(
            telemetry,
            down_services,
        )

        title = (
            "Incident: Infrastructure Degradation "
            f"({', '.join(detection['anomalies'][:2])})"
        )

        cause = (
            f"Detected {detection['anomaly_count']} "
            f"system anomaly/anomalies: "
            f"{'; '.join(detection['anomalies'])}."
        )

        runbook_titles = {match["title"] for match in runbook_matches}

        actions = self._build_actions(
            runbook_titles,
            down_services,
        )

        escalation_required = severity in {
            SeverityLevel.HIGH,
            SeverityLevel.CRITICAL,
        }

        escalation_criteria = self._build_escalation_criteria(
            runbook_titles,
            down_services,
            escalation_required,
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
