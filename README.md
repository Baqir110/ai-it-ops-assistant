# AI IT Operations Assistant

An infrastructure-focused AIOps platform for automated telemetry analysis, anomaly detection, runbook retrieval, incident triage, monitoring, visualization, and alerting.

Built with FastAPI, PostgreSQL, Redis, Prometheus, Grafana, Docker, and Kubernetes, the project demonstrates a production-oriented backend architecture for IT operations and observability workflows.

[![CI](https://github.com/Baqir110/ai-it-ops-assistant/actions/workflows/ci.yml/badge.svg)](https://github.com/Baqir110/ai-it-ops-assistant/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python\&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-API-009688.svg?logo=fastapi\&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1.svg?logo=postgresql\&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D.svg?logo=redis\&logoColor=white)](https://redis.io/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Monitoring-E6522C.svg?logo=prometheus\&logoColor=white)](https://prometheus.io/)
[![Grafana](https://img.shields.io/badge/Grafana-Dashboard%20%26%20Alerting-F46800.svg?logo=grafana\&logoColor=white)](https://grafana.com/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker\&logoColor=white)](https://www.docker.com/)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Ready-326CE5.svg?logo=kubernetes\&logoColor=white)](https://kubernetes.io/)
[![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Overview

AI IT Operations Assistant analyzes infrastructure telemetry and converts detected operational problems into structured incident reports.

The platform processes signals such as:

* CPU utilization
* RAM utilization
* Disk utilization
* Service availability
* HTTP endpoint health
* Request latency
* Operational anomalies

Telemetry is evaluated by a rule-based anomaly detection engine. Detected anomalies can be correlated with operational runbooks to provide troubleshooting context and recommended actions.

The application also exposes Prometheus-compatible metrics. Prometheus collects the metrics, while Grafana provides dashboards, alert evaluation, alert routing, and email notifications.

The resulting incident report can contain:

* Incident title
* Severity
* Detected anomalies
* Likely cause
* Recommended actions
* Escalation decision
* Escalation criteria
* Supporting runbooks

---

# Architecture

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

    subgraph Observability["Monitoring and Alerting"]

        Prom["Prometheus"]

        Grafana["Grafana Dashboard"]

        Alerting["Grafana Alerting"]

        Email["Email Notifications"]

    end

    Client -->|"Telemetry"| API

    API --> Engine

    Engine --> RAG

    RAG --> Runbooks

    Engine --> Synth

    RAG --> Synth

    Synth -->|"Incident Report"| API

    API --> PG

    API --> Redis

    API -->|"/metrics"| Prom

    Prom --> Grafana

    Grafana --> Alerting

    Alerting --> Email

    API -->|"Structured Response"| Client
```

---

# Monitoring and Alerting Flow

```text
Infrastructure Telemetry
        |
        v
FastAPI API
        |
        +----------------------+
        |                      |
        v                      v
Anomaly Detection         /metrics
        |                      |
        v                      v
Incident Analysis       Prometheus
        |                      |
        v                      v
Incident Report         Grafana
                               |
                               v
                        Dashboard Panels
                               |
                               v
                        Alert Evaluation
                               |
                               v
                        Notification Policy
                               |
                               v
                        Email Notification
```

---

# Key Features

## Automated Anomaly Detection

Configurable rules detect infrastructure conditions that require investigation.

Currently supported signals include:

* CPU utilization
* RAM utilization
* Disk utilization
* Service availability
* HTTP endpoint failures

## Runbook-Assisted Incident Analysis

Detected anomalies can be matched against operational runbooks stored as Markdown documents.

Current runbooks include:

* High CPU utilization
* Memory pressure
* Disk and web server issues
* Service outages

The retrieval layer provides operational context without requiring the incident responder to manually search documentation.

## Structured Incident Reports

Incident responses use typed Pydantic models rather than unstructured text.

This makes the output suitable for:

* Monitoring integrations
* Alerting pipelines
* Incident-management systems
* Automated remediation workflows
* Future LLM-based summarization

## REST API

The FastAPI backend provides:

* Telemetry analysis
* Health checks
* Readiness checks
* Authentication endpoints
* Prometheus metrics
* OpenAPI documentation

## Prometheus Monitoring

The application exposes Prometheus-compatible metrics.

Current infrastructure metrics include:

```text
itops_cpu_percent
itops_ram_percent
itops_disk_percent
```

Prometheus target availability can be queried with:

```promql
up{job="ai-it-ops"}
```

A value of `1` indicates that Prometheus considers the API target available.

## Grafana Dashboard

Grafana is configured as the visualization layer for the monitoring stack.

The dashboard provides visibility into:

* CPU utilization
* RAM utilization
* Disk utilization
* API and service health
* Request latency
* Detected anomalies
* Infrastructure state

Prometheus is used as the Grafana data source.

## Grafana Alerting

Grafana-managed alert rules monitor the application metrics and operational signals.

The current alert rules include:

| Alert                     | Condition                                                   | Severity |
| ------------------------- | ----------------------------------------------------------- | -------- |
| High CPU Utilization      | CPU usage exceeds the configured threshold                  | Critical |
| High RAM Utilization      | RAM usage exceeds the configured threshold                  | Critical |
| Critical Disk Utilization | Disk usage exceeds 90%                                      | Critical |
| High Request Latency      | 95th percentile request latency exceeds 1 second            | Critical |
| Anomalies Detected        | One or more anomalies detected within the evaluation window | Critical |

The alerts are evaluated by Grafana and routed through the configured notification policy.

## Email Notifications

Grafana Alerting is configured with an email contact point.

The notification pipeline is:

```text
Grafana Alert Rule
        |
        v
Grafana Alertmanager
        |
        v
Notification Policy
        |
        v
AI IT Operations Email Contact Point
        |
        v
SMTP
        |
        v
Email Notification
```

The alerting configuration has been verified through the Grafana Alertmanager API.

The following alerts were successfully observed as active:

* High Request Latency
* Critical Disk Utilization
* High RAM Utilization
* Anomalies Detected
* High CPU Utilization

Grafana logs also confirmed successful email notification delivery.

Example successful notification log:

```text
receiver="AI IT Operations Email"
integration=email
msg="Notify success"
attempts=1
```

Resolved alert notifications were also successfully processed.

## Docker Support

Docker Compose provides a complete local development environment containing:

* FastAPI
* PostgreSQL
* Redis
* Prometheus
* Grafana
* Grafana alerting and notification configuration

## Kubernetes Support

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

# Technology Stack

| Category          | Technology                           |
| ----------------- | ------------------------------------ |
| Language          | Python 3.11+                         |
| API Framework     | FastAPI                              |
| Validation        | Pydantic                             |
| Database          | PostgreSQL 16                        |
| Cache             | Redis 7                              |
| Monitoring        | Prometheus                           |
| Visualization     | Grafana                              |
| Alerting          | Grafana Alerting                     |
| Notifications     | SMTP Email                           |
| Containerization  | Docker                               |
| Orchestration     | Kubernetes                           |
| Testing           | pytest                               |
| HTTP Client       | HTTPX                                |
| CI                | GitHub Actions                       |
| Configuration     | Environment Variables                |
| Runbook Knowledge | Markdown                             |
| Retrieval         | ChromaDB / Embedding-Based Retrieval |

---

# Repository Structure

```text
ai-it-ops-assistant/
|
├── .github/
│   └── workflows/
│       └── ci.yml
|
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
|
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
|
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
|
├── prometheus/
│   └── prometheus.yml
|
├── tests/
│   ├── test_api.py
│   ├── test_auth.py
│   └── test_engine.py
|
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

# Docker Compose

Docker Compose is the recommended method for running the complete local monitoring stack.

## 1. Clone the Repository

```bash
git clone https://github.com/Baqir110/ai-it-ops-assistant.git
cd ai-it-ops-assistant
```

## 2. Configure Environment Variables

Create a local `.env` file containing the required configuration.

Do not commit real credentials, API keys, SMTP passwords, tokens, or production secrets.

## 3. Start the Stack

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

## 4. Verify the API

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

The API is available at:

```text
http://localhost:8000
```

Interactive API documentation:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

# Prometheus

Prometheus collects metrics exposed by the FastAPI application.

When running with Docker Compose, Prometheus is available at:

```text
http://localhost:9090
```

## Verify Metrics

Open the Prometheus query interface and query:

```promql
itops_cpu_percent
```

```promql
itops_ram_percent
```

```promql
itops_disk_percent
```

Check API availability:

```promql
up{job="ai-it-ops"}
```

A value of:

```text
1
```

indicates that the target is available.

---

# Grafana

When running through Docker Compose, Grafana is available at:

```text
http://localhost:3000
```

The local development credentials are configured in `docker-compose.yml`.

Change development credentials before deploying outside a local environment.

Grafana provides:

* Infrastructure monitoring dashboard
* Prometheus data source integration
* Alert rule evaluation
* Notification policies
* Email alert notifications

The current monitoring setup includes alert rules for CPU, RAM, disk utilization, request latency, and detected anomalies.

---

# Verifying Grafana Alerts

The Grafana Alertmanager API can be queried to inspect active alerts:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3000/api/alertmanager/grafana/api/v2/alerts" `
  -Headers $Headers |
  ConvertTo-Json -Depth 20
```

The alert state can report:

```text
active
```

The current configuration successfully detected multiple critical conditions simultaneously, including:

```text
High Request Latency
Critical Disk Utilization
High RAM Utilization
Anomalies Detected
High CPU Utilization
```

Verify configured contact points:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3000/api/v1/provisioning/contact-points" `
  -Headers $Headers |
  ConvertTo-Json -Depth 20
```

Verify the notification policy:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:3000/api/v1/provisioning/policies" `
  -Headers $Headers |
  ConvertTo-Json -Depth 20
```

The policy routes alerts to:

```text
AI IT Operations Email
```

Grafana logs can be checked for notification delivery:

```powershell
docker compose logs grafana --tail=100 |
Select-String -Pattern "smtp|email|notification|sent|error|failed"
```

A successful notification contains:

```text
msg="Notify success"
```

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

Never commit real credentials, SMTP passwords, API keys, or production secrets.

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

GitHub Actions provides automated CI validation.

The CI workflow is located at:

```text
.github/workflows/ci.yml
```

The pipeline provides an automated quality gate for changes pushed to the repository.

---

# Kubernetes Deployment

Kubernetes manifests are located under `k8s/`.

Apply the core resources:

```powershell
kubectl apply -f .\k8s\
```

Apply Prometheus monitoring:

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

Expose the API locally:

```powershell
kubectl port-forward -n ai-it-ops service/ai-it-ops-api 8000:8000
```

Verify readiness:

```powershell
Invoke-RestMethod http://localhost:8000/ready
```

A healthy deployment should report dependency connectivity.

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

# Current Validation

The monitoring and alerting pipeline has been validated locally.

The verified architecture is:

```text
FastAPI
   |
   | /metrics
   v
Prometheus
   |
   | PromQL
   v
Grafana Dashboard
   |
   | Alert Rules
   v
Grafana Alerting
   |
   | Notification Policy
   v
Email Contact Point
   |
   v
Email Notification
```

The following Grafana alerts were successfully observed in the active state:

```text
High CPU Utilization
High RAM Utilization
Critical Disk Utilization
High Request Latency
Anomalies Detected
```

Grafana notification logs confirmed successful delivery to the configured email contact point.

This validates the complete monitoring and alerting flow from application telemetry to notification delivery.

The reported infrastructure values are demonstration data and should not be interpreted as production infrastructure capacity.

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
* Grafana dashboards
* Grafana-managed alerting
* Email notifications
* Health and readiness checks
* Automated testing
* GitHub Actions CI
* Configuration management
* Secret management
* Infrastructure-oriented software design

---

# Roadmap

Planned improvements include:

* Slack notifications
* Microsoft Teams notifications
* Automated remediation workflows
* Kubernetes autoscaling
* Persistent Prometheus storage
* PostgreSQL backup automation
* Improved authentication and authorization
* LLM-assisted incident summarization
* Incident history and operational analytics
* Web-based operations dashboard
* Advanced alert grouping and escalation policies
* Alert silencing and maintenance windows
* Infrastructure-as-code provisioning for Grafana dashboards and alert rules

---

# Contributing

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

GitHub: [Baqir110 on GitHub](https://github.com/Baqir110?utm_source=chatgpt.com)

LinkedIn: [Muhammad Baqir on LinkedIn](https://www.linkedin.com/in/muhammad-baqir-it/?utm_source=chatgpt.com)
