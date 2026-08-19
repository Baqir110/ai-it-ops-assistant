# AI IT Operations Assistant

An infrastructure-focused AIOps platform for automated telemetry analysis, anomaly detection, runbook retrieval, and incident triage.

Built with FastAPI, PostgreSQL, Redis, Prometheus, Grafana, Docker, and Kubernetes, the project demonstrates a production-oriented backend architecture for IT operations and observability workflows.

[![CI](https://github.com/Baqir110/ai-it-ops-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Baqir110/ai-it-ops-assistant/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis&logoColor=white)](https://redis.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-3.5-E6522C.svg?logo=prometheus&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-12.1-F46800.svg?logo=grafana&logoColor=white)](https://grafana.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg?logo=kubernetes&logoColor=white)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Overview

AI IT Operations Assistant analyzes infrastructure telemetry and converts detected operational problems into structured incident reports.

The system accepts signals such as:

- CPU utilization
- RAM utilization
- Disk utilization
- Service availability
- HTTP endpoint health
- Operational events

Telemetry is evaluated by a rule-based anomaly detection engine. Detected anomalies can then be correlated with operational runbooks to provide troubleshooting context and recommended actions.

The resulting incident report contains structured information such as:

- Incident title
- Severity
- Detected anomalies
- Likely cause
- Recommended actions
- Escalation decision
- Escalation criteria
- Supporting runbooks

The platform also exposes Prometheus metrics and can be visualized through Grafana.

---

## Architecture

```mermaid
flowchart TB

    Client["Client / Monitoring Agent"]

    subgraph Platform["AI IT Operations Platform"]

        API["FastAPI API"]

        Engine["Anomaly Detection Engine"]

        RAG["Runbook Retrieval"]

        Synth["Incident Synthesizer"]

        PG[("PostgreSQL")]

        Redis[("Redis")]

    end

    Runbooks[("Operational Runbooks")]

    subgraph Observability["Observability"]

        Prom["Prometheus"]

        Grafana["Grafana"]

    end

    Client -->|"Telemetry"| API

    API --> Engine

    Engine --> RAG

    RAG --> Runbooks

    RAG --> Synth

    Engine --> Synth

    Synth -->|"Incident Report"| API

    API --> PG

    API --> Redis

    API -->|"/metrics"| Prom

    Prom --> Grafana

    API -->|"Structured Response"| Client
````

### Processing Flow

```text
Telemetry
    |
    v
FastAPI API
    |
    v
Anomaly Detection
    |
    +-- CPU threshold
    +-- RAM threshold
    +-- Disk threshold
    +-- Service availability
    +-- HTTP endpoint health
    |
    v
Runbook Retrieval
    |
    v
Incident Synthesis
    |
    v
Structured Incident Report
    |
    +-- Severity
    +-- Likely Cause
    +-- Recommended Actions
    +-- Escalation Decision
    +-- Supporting Runbooks
```

---

## Key Features

### Automated anomaly detection

Configurable rules detect infrastructure conditions that require investigation.

Currently supported signals include:

* CPU utilization
* RAM utilization
* Disk utilization
* Service availability
* HTTP endpoint failures

### Runbook-assisted incident analysis

Detected anomalies can be matched against operational runbooks stored as Markdown documents.

Current runbooks include:

* High CPU
* Memory pressure
* Disk and web server issues
* Service outages

The retrieval layer is designed to provide operational context without requiring the incident responder to manually search documentation.

### Structured incident reports

Incident responses are represented using typed Pydantic models rather than unstructured text.

This makes the output suitable for:

* Monitoring integrations
* Alerting pipelines
* Incident-management systems
* Automated remediation workflows
* Future LLM-based summarization

### REST API

The FastAPI backend provides:

* Telemetry analysis
* Health checks
* Readiness checks
* Authentication endpoints
* Prometheus metrics
* OpenAPI documentation

### Observability

The application exposes Prometheus-compatible metrics including:

```text
itops_cpu_percent
itops_ram_percent
itops_disk_percent
```

Prometheus target health is available through:

```promql
up{job="ai-it-ops"}
```

### Docker support

Docker Compose provides a complete local development environment containing:

* FastAPI
* PostgreSQL
* Redis
* Prometheus
* Grafana

### Kubernetes support

Kubernetes manifests are provided for:

* API deployment
* API service
* API configuration
* API secrets
* PostgreSQL
* Redis
* Prometheus
* Persistent PostgreSQL storage

---

## Technology Stack

| Category          | Technology                           |
| ----------------- | ------------------------------------ |
| Language          | Python 3.11+                         |
| API Framework     | FastAPI                              |
| Validation        | Pydantic                             |
| Database          | PostgreSQL 16                        |
| Cache             | Redis 7                              |
| Monitoring        | Prometheus 3.5                       |
| Visualization     | Grafana 12.1                         |
| Containerization  | Docker                               |
| Orchestration     | Kubernetes                           |
| Testing           | pytest                               |
| HTTP Client       | HTTPX                                |
| CI                | GitHub Actions                       |
| Configuration     | Environment variables                |
| Runbook Knowledge | Markdown                             |
| Retrieval         | ChromaDB / embedding-based retrieval |

---

## Repository Structure

```text
ai-it-ops-assistant/
|
├── .github/
│   └── workflows/
│       └── ci.yml
│
├── app/
│   ├── api/
│   │   ├── endpoints.py
│   │   ├── health.py
│   │   └── v1/
│   │       └── auth.py
│   │
│   ├── auth/
│   │   ├── dependencies.py
│   │   └── security.py
│   │
│   ├── cache/
│   │   └── redis.py
│   │
│   ├── config/
│   │   └── settings.py
│   │
│   ├── database/
│   │   ├── connection.py
│   │   ├── models.py
│   │   └── repositories.py
│   │
│   ├── engine/
│   │   ├── anomaly_detector.py
│   │   └── rules.py
│   │
│   ├── models/
│   │   ├── audit.py
│   │   ├── incident.py
│   │   ├── schemas.py
│   │   ├── telemetry.py
│   │   └── user.py
│   │
│   ├── monitoring/
│   │   └── metrics.py
│   │
│   ├── rag/
│   │   └── runbook_search.py
│   │
│   ├── services/
│   │   └── synthesizer.py
│   │
│   ├── logging_config.py
│   └── main.py
│
├── data/
│   ├── runbooks/
│   │   ├── disk_and_webserver.md
│   │   ├── high_cpu.md
│   │   ├── memory_pressure.md
│   │   └── service_outage.md
│   │
│   ├── telemetry_samples/
│   │   └── sample_payload.json
│   │
│   └── degraded_server.json
│
├── k8s/
│   ├── api-config.yaml
│   ├── api-deployment.yaml
│   ├── api-secret.yaml
│   ├── api-service.yaml
│   ├── postgres.yaml
│   ├── redis.yaml
│   │
│   └── monitoring/
│       ├── prometheus-config.yaml
│       ├── prometheus-deployment.yaml
│       └── prometheus-service.yaml
│
├── prometheus/
│   └── prometheus.yml
│
├── tests/
│   ├── test_api.py
│   ├── test_auth.py
│   └── test_engine.py
│
├── .dockerignore
├── .gitignore
├── docker-compose.yml
├── Dockerfile
├── gunicorn.conf.py
├── pytest.ini
├── requirements.txt
├── setup-grafana.ps1
└── README.md
```

---

# Getting Started

## Prerequisites

For Docker-based development:

* Docker Desktop
* Git

For local Python development:

* Python 3.11+
* pip
* Git

For Kubernetes deployment:

* Kubernetes cluster
* kubectl
* Container image available to the cluster

---

## Docker Compose

Docker Compose is the recommended method for running the complete local stack.

### 1. Clone the repository

```bash
git clone https://github.com/Baqir110/ai-it-ops-assistant.git
cd ai-it-ops-assistant
```

### 2. Configure environment variables

Create a local `.env` file containing the required configuration.

Do not commit real credentials, API keys, tokens, or production secrets.

### 3. Start the stack

```bash
docker compose up -d --build
```

Check service status:

```bash
docker compose ps
```

View logs:

```bash
docker compose logs -f
```

### 4. Verify the API

```bash
curl http://localhost:8000/health
```

Check dependency readiness:

```bash
curl http://localhost:8000/ready
```

The readiness endpoint verifies connectivity to required dependencies such as PostgreSQL, Redis, and the vector store.

---

# Local Python Development

Create a virtual environment:

```bash
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

Interactive Swagger documentation:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

# Kubernetes Deployment

Kubernetes manifests are located under `k8s/`.

The current local deployment consists of:

```text
ai-it-ops
|
├── AI IT Operations API
├── PostgreSQL
├── Redis
└── Prometheus
```

Apply the core resources:

```powershell
kubectl apply -f .\k8s\
```

Apply Prometheus:

```powershell
kubectl apply -f .\k8s\monitoring\
```

Verify workloads:

```powershell
kubectl get pods -n ai-it-ops
```

Check services:

```powershell
kubectl get services -n ai-it-ops
```

Check all resources:

```powershell
kubectl get all -n ai-it-ops
```

---

# Kubernetes API Verification

Expose the API locally:

```powershell
kubectl port-forward -n ai-it-ops service/ai-it-ops-api 8000:8000
```

Verify readiness:

```powershell
Invoke-RestMethod http://localhost:8000/ready
```

A healthy deployment should report dependency connectivity similar to:

```text
status: ready

checks:
  postgres: connected
  redis: connected
  vector_store: available
```

---

# Prometheus

Prometheus is configured to scrape the Kubernetes API service through its internal DNS name:

```text
ai-it-ops-api.ai-it-ops.svc.cluster.local:8000
```

The Kubernetes scrape configuration is located at:

```text
k8s/monitoring/prometheus-config.yaml
```

Expose Prometheus locally:

```powershell
kubectl port-forward -n ai-it-ops service/prometheus 9090:9090
```

Open:

```text
http://localhost:9090
```

## Verify the scrape target

```powershell
Invoke-RestMethod "http://localhost:9090/api/v1/targets"
```

The API target should report:

```text
health: up
```

## Query application metrics

CPU:

```powershell
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=itops_cpu_percent"
```

RAM:

```powershell
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=itops_ram_percent"
```

Disk:

```powershell
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=itops_disk_percent"
```

Target availability:

```powershell
Invoke-RestMethod "http://localhost:9090/api/v1/query?query=up{job='ai-it-ops'}"
```

A value of:

```text
1
```

indicates that Prometheus considers the API target available.

---

# Grafana

When running through Docker Compose, Grafana is available at:

```text
http://localhost:3000
```

The local development credentials are configured in `docker-compose.yml`.

Change default credentials before using the system outside a local development environment.

Grafana can visualize:

* CPU utilization
* RAM utilization
* Disk utilization
* API availability
* Application health
* Incident-related metrics

Prometheus is used as the metrics data source.

---

# API

## Analyze Infrastructure Telemetry

Endpoint:

```http
POST /api/v1/telemetry/analyze
```

Example request:

```json
{
  "cpu_percent": 94.0,
  "ram_percent": 91.0,
  "disk_percent": 97.0,
  "services": {
    "apache2": "DOWN"
  },
  "http_endpoints": {
    "https://app.internal/health": 503
  }
}
```

Example response:

```json
{
  "incident_title": "Infrastructure degradation detected",
  "severity": "CRITICAL",
  "likely_cause": "Multiple infrastructure health indicators exceeded configured thresholds.",
  "recommended_actions": [
    "Inspect system and application logs.",
    "Identify processes consuming excessive resources.",
    "Free disk capacity.",
    "Attempt service recovery."
  ],
  "escalation_required": true,
  "escalation_criteria": "Escalate when service recovery fails or critical resource thresholds remain exceeded.",
  "sources_consulted": [
    {
      "title": "disk_and_webserver.md",
      "relevance_score": 0.58
    }
  ]
}
```

The authoritative response schema is defined by the application's Pydantic models.

---

# API Endpoints

| Endpoint                    | Purpose                           |
| --------------------------- | --------------------------------- |
| `/health`                   | Application health check          |
| `/ready`                    | Dependency readiness check        |
| `/metrics`                  | Prometheus metrics                |
| `/docs`                     | Swagger / OpenAPI documentation   |
| `/redoc`                    | ReDoc documentation               |
| `/api/v1/telemetry/analyze` | Infrastructure telemetry analysis |

---

# Configuration

Runtime configuration is controlled through environment variables.

| Variable            | Purpose                      |
| ------------------- | ---------------------------- |
| `DATABASE_URL`      | PostgreSQL connection string |
| `REDIS_URL`         | Redis connection string      |
| `OPENAI_API_KEY`    | Optional LLM integration     |
| `CPU_THRESHOLD`     | CPU anomaly threshold        |
| `RAM_THRESHOLD`     | RAM anomaly threshold        |
| `DISK_THRESHOLD`    | Disk anomaly threshold       |
| `VECTOR_STORE_PATH` | Vector store location        |
| `RUNBOOKS_PATH`     | Runbook directory            |
| `LOG_LEVEL`         | Application logging level    |

Example:

```env
DATABASE_URL=postgresql+psycopg://ops:ops@postgres:5432/ops
REDIS_URL=redis://redis:6379/0

CPU_THRESHOLD=85.0
RAM_THRESHOLD=85.0
DISK_THRESHOLD=90.0

VECTOR_STORE_PATH=./data/vector_store
RUNBOOKS_PATH=./data/runbooks

LOG_LEVEL=info
```

Never commit real credentials or production secrets.

---

# Testing

The project uses pytest for automated testing.

Run the complete test suite:

```bash
pytest
```

Verbose output:

```bash
pytest -v
```

API tests:

```bash
pytest tests/test_api.py -v
```

Authentication tests:

```bash
pytest tests/test_auth.py -v
```

Anomaly detection tests:

```bash
pytest tests/test_engine.py -v
```

Continuous integration is configured through:

```text
.github/workflows/ci.yml
```

---

# CI/CD

GitHub Actions provides automated CI validation through:

```text
.github/workflows/ci.yml
```

The CI pipeline is intended to provide an automated quality gate for changes pushed to the repository.

---

# Security Considerations

This repository is primarily an engineering and portfolio project.

Before production deployment, the following areas should be addressed:

* Replace development credentials.
* Store secrets using Kubernetes Secrets or an external secret manager.
* Do not expose PostgreSQL or Redis publicly.
* Enable HTTPS/TLS through an ingress or reverse proxy.
* Run application containers as a non-root user.
* Define CPU and memory requests and limits.
* Add Kubernetes NetworkPolicies.
* Configure persistent storage for monitoring data.
* Implement PostgreSQL backup and recovery.
* Implement production-grade authentication and authorization.
* Add rate limiting where appropriate.
* Pin and regularly update dependencies.
* Scan container images for vulnerabilities.
* Configure appropriate logging and audit retention.
* Use production-grade PostgreSQL and Redis configurations.

---

# Current Kubernetes Validation

The Kubernetes deployment has been validated locally.

Core workloads successfully running:

```text
ai-it-ops-api
postgres
redis
prometheus
```

Prometheus successfully discovers the API through:

```text
ai-it-ops-api.ai-it-ops.svc.cluster.local:8000
```

The Prometheus target reports:

```text
health: up
```

Application metrics have also been successfully queried through the Prometheus HTTP API:

```text
itops_cpu_percent
itops_ram_percent
itops_disk_percent
```

This confirms the current monitoring path:

```text
API
 |
 | /metrics
 v
Prometheus
 |
 | PromQL
 v
Monitoring / Grafana
```

The reported telemetry values are demonstration data and should not be interpreted as production infrastructure capacity.

---

# Project Goals

This project demonstrates practical implementation of:

* REST API development
* Backend application architecture
* Infrastructure telemetry processing
* Rule-based anomaly detection
* Runbook-assisted incident analysis
* PostgreSQL persistence
* Redis caching
* Containerization
* Kubernetes deployment
* Prometheus monitoring
* Grafana observability
* Health and readiness checks
* Automated testing
* GitHub Actions CI
* Configuration management
* Secret management
* Infrastructure-oriented software design

---

# Roadmap

Planned improvements include:

* More comprehensive Prometheus alerting rules
* Production-ready Grafana dashboards
* Alertmanager integration
* Slack and Microsoft Teams notifications
* Automated remediation workflows
* Kubernetes autoscaling
* Persistent Prometheus storage
* PostgreSQL backup automation
* Improved authentication and authorization
* LLM-assisted incident summarization
* Incident history and operational analytics
* Web-based operations dashboard

---

# Contributing

Contributions are welcome.

Create a feature branch:

```bash
git checkout -b feature/your-feature
```

Run the test suite:

```bash
pytest -v
```

Commit your changes:

```bash
git commit -m "Add your change"
```

Push the branch:

```bash
git push origin feature/your-feature
```

Then open a Pull Request.

---

# License

This project is licensed under the MIT License.

See [LICENSE](LICENSE) for details.

---

# Author

**Muhammad Baqir**

GitHub: [https://github.com/Baqir110](https://github.com/Baqir110)

LinkedIn: [https://www.linkedin.com/in/muhammad-baqir-it/](https://www.linkedin.com/in/muhammad-baqir-it/)

