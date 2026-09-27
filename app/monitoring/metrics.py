"""Prometheus metrics for OpsGuard."""

from prometheus_client import Counter, Gauge, Histogram

# --- API Metrics ---
TELEMETRY_REQUESTS = Counter(
    "opsguard_telemetry_requests_total", "Total telemetry analysis requests"
)
INCIDENTS_CREATED = Counter(
    "opsguard_incidents_created_total", "Total incidents created", ["severity"]
)
ANOMALIES_DETECTED = Counter(
    "opsguard_anomalies_detected_total", "Total anomalies detected"
)
REQUEST_LATENCY = Histogram(
    "opsguard_request_latency_seconds", "Request latency in seconds"
)

# --- System Metrics ---
CPU_USAGE = Gauge("opsguard_cpu_percent", "Latest reported CPU utilization")
RAM_USAGE = Gauge("opsguard_ram_percent", "Latest reported RAM utilization")
DISK_USAGE = Gauge("opsguard_disk_percent", "Latest reported disk utilization")

# --- HTTP Monitor Metrics ---
HTTP_CHECKS_TOTAL = Counter(
    "opsguard_http_checks_total", "Total HTTP health checks", ["service", "result"]
)
HTTP_CHECK_LATENCY = Histogram(
    "opsguard_http_check_latency_seconds", "HTTP check latency", ["service"]
)
HTTP_DETECTIONS = Counter(
    "opsguard_http_detections_total", "HTTP-based detections", ["type"]
)

# --- Prometheus Detector Metrics ---
PROMETHEUS_DETECTIONS = Counter(
    "opsguard_prometheus_detections_total", "Prometheus-based detections", ["type"]
)

# --- Incident Lifecycle Metrics ---
INCIDENT_STATUS_CHANGES = Counter(
    "opsguard_incident_status_changes_total",
    "Incident status changes",
    ["from_status", "to_status"],
)
EVIDENCE_COLLECTIONS = Counter(
    "opsguard_evidence_collections_total", "Evidence items collected"
)
DIAGNOSES_CREATED = Counter(
    "opsguard_diagnoses_created_total", "Total diagnoses created"
)
REMEDIATION_ACTIONS = Counter(
    "opsguard_remediation_actions_total",
    "Remediation actions",
    ["action_type", "result"],
)
VERIFICATION_RUNS = Counter(
    "opsguard_verification_runs_total", "Recovery verification runs"
)
SLO_MEASUREMENTS = Counter(
    "opsguard_slo_measurements_total", "SLO measurements", ["slo", "within_target"]
)
COST_RECOMMENDATIONS = Counter(
    "opsguard_cost_recommendations_total", "Cost recommendations", ["category"]
)

# --- SRE Metrics ---
MTTD = Gauge("opsguard_mttd_minutes", "Mean time to detect in minutes")
MTTR = Gauge("opsguard_mttr_minutes", "Mean time to resolve in minutes")
ACTIVE_INCIDENTS = Gauge("opsguard_active_incidents", "Number of active incidents")
