from prometheus_client import Counter, Gauge, Histogram

TELEMETRY_REQUESTS = Counter(
    "itops_telemetry_requests_total", "Total telemetry analysis requests"
)
INCIDENTS_CREATED = Counter(
    "itops_incidents_created_total", "Total incidents persisted", ["severity"]
)
ANOMALIES_DETECTED = Counter(
    "itops_anomalies_detected_total", "Total anomalies detected"
)
REQUEST_LATENCY = Histogram(
    "itops_request_latency_seconds", "Telemetry analysis request latency"
)
CPU_USAGE = Gauge("itops_cpu_percent", "Latest reported CPU utilization")
RAM_USAGE = Gauge("itops_ram_percent", "Latest reported RAM utilization")
DISK_USAGE = Gauge("itops_disk_percent", "Latest reported disk utilization")
