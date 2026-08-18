from typing import Dict, Any
from app.models.schemas import SystemTelemetry
from app.config.settings import settings


class AnomalyDetector:
    def evaluate(self, telemetry: SystemTelemetry) -> Dict[str, Any]:
        anomalies = []

        # Resource Threshold Checks
        if telemetry.cpu_percent >= settings.CPU_THRESHOLD:
            anomalies.append(f"High CPU utilization: {telemetry.cpu_percent}%")

        if telemetry.ram_percent >= settings.RAM_THRESHOLD:
            anomalies.append(f"High RAM utilization: {telemetry.ram_percent}%")

        if telemetry.disk_percent >= settings.DISK_THRESHOLD:
            anomalies.append(f"Critical Disk utilization: {telemetry.disk_percent}%")

        # Service Health Checks
        for service, status in telemetry.services.items():
            if status.upper() in ["DOWN", "STOPPED", "FAILED"]:
                anomalies.append(f"Service outage: {service} is {status.upper()}")

        # Endpoint Health Checks
        for endpoint, code in telemetry.http_endpoints.items():
            if code >= 400:
                anomalies.append(f"Endpoint failure: {endpoint} returned HTTP {code}")

        return {
            "has_anomalies": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
        }
