from math import erf, sqrt
from statistics import mean, pstdev
from typing import Any, Dict, List

from app.cache.redis import get_metric_history, push_metric_sample
from app.config.settings import settings
from app.models.schemas import SystemTelemetry


class AnomalyDetector:
    """
    Hybrid infrastructure anomaly detector.

    Detection combines:
    1. Absolute operational thresholds.
    2. Rolling historical baselines stored in Redis.
    3. Z-score statistical anomaly detection.
    4. Confidence scoring based on statistical distance.
    """

    MIN_HISTORY = 5
    Z_SCORE_THRESHOLD = 3.0

    METRIC_LABELS = {
        "cpu": "CPU",
        "memory": "RAM",
        "disk": "Disk",
    }

    def evaluate_metric(
        self,
        service_name: str,
        metric_name: str,
        value: float,
        threshold: float | None = None,
    ) -> Dict[str, Any]:
        """
        Evaluate one metric against its operational threshold
        and historical statistical baseline.
        """

        history = get_metric_history(
            service_name,
            metric_name,
        )

        # Calculate the baseline BEFORE adding the current sample.
        baseline_available = len(history) >= self.MIN_HISTORY

        baseline_mean = None
        baseline_std = None
        z_score = 0.0

        if baseline_available:
            baseline_mean = mean(history)
            baseline_std = pstdev(history)

            if baseline_std > 0:
                z_score = abs(value - baseline_mean) / baseline_std

        statistical_anomaly = baseline_available and z_score >= self.Z_SCORE_THRESHOLD

        threshold_anomaly = threshold is not None and value >= threshold

        anomaly = statistical_anomaly or threshold_anomaly

        confidence = self._calculate_confidence(
            z_score=z_score,
            statistical_anomaly=statistical_anomaly,
            threshold_anomaly=threshold_anomaly,
        )

        # Store current sample AFTER calculating the baseline.
        push_metric_sample(
            service_name,
            metric_name,
            value,
        )

        return {
            "metric": metric_name,
            "value": value,
            "anomaly": anomaly,
            "confidence": round(confidence, 4),
            "z_score": round(z_score, 4),
            "baseline_mean": (
                round(baseline_mean, 4) if baseline_mean is not None else None
            ),
            "baseline_std": (
                round(baseline_std, 4) if baseline_std is not None else None
            ),
            "statistical_anomaly": statistical_anomaly,
            "threshold_anomaly": threshold_anomaly,
        }

    def _calculate_confidence(
        self,
        z_score: float,
        statistical_anomaly: bool,
        threshold_anomaly: bool,
    ) -> float:
        """
        Calculate a bounded confidence score.

        Statistical anomalies use the distance from the historical
        baseline. Threshold-only anomalies receive a conservative
        confidence because there may not yet be enough history.
        """

        if statistical_anomaly:
            tail_probability = 0.5 * (1.0 - erf(z_score / sqrt(2.0)))

            confidence = 1.0 - (2.0 * tail_probability)

            return max(
                0.0,
                min(confidence, 0.9999),
            )

        if threshold_anomaly:
            return 0.50

        return 0.0

    def evaluate(
        self,
        telemetry: SystemTelemetry,
    ) -> Dict[str, Any]:
        """
        Evaluate complete system telemetry.

        Returns anomaly descriptions plus detailed metric
        analysis for downstream incident synthesis.
        """

        anomalies: List[str] = []
        metric_results: List[Dict[str, Any]] = []

        metrics = [
            (
                "system",
                "cpu",
                telemetry.cpu_percent,
                settings.CPU_THRESHOLD,
            ),
            (
                "system",
                "memory",
                telemetry.ram_percent,
                settings.RAM_THRESHOLD,
            ),
            (
                "system",
                "disk",
                telemetry.disk_percent,
                settings.DISK_THRESHOLD,
            ),
        ]

        for (
            service_name,
            metric_name,
            value,
            threshold,
        ) in metrics:

            result = self.evaluate_metric(
                service_name=service_name,
                metric_name=metric_name,
                value=value,
                threshold=threshold,
            )

            metric_results.append(result)

            if result["anomaly"]:
                label = self.METRIC_LABELS.get(
                    metric_name,
                    metric_name.upper(),
                )

                confidence = result["confidence"]

                anomalies.append(
                    f"High {label} utilization: "
                    f"{value}% "
                    f"(confidence={confidence:.2f})"
                )

        # Service health checks.
        for service, service_status in telemetry.services.items():
            normalized_status = service_status.upper()

            if normalized_status in {
                "DOWN",
                "STOPPED",
                "FAILED",
                "UNHEALTHY",
            }:
                anomalies.append(
                    f"Service outage: " f"{service} is {normalized_status}"
                )

        # HTTP endpoint health checks.
        for endpoint, code in telemetry.http_endpoints.items():
            if code >= 400:
                anomalies.append(
                    f"Endpoint failure: " f"{endpoint} returned HTTP {code}"
                )

        return {
            "has_anomalies": bool(anomalies),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "metrics": metric_results,
        }
