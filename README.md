# AI-Powered IT Operations Assistant

An automated AIOps incident triage engine built with FastAPI, LangChain, ChromaDB, and Pydantic. The platform ingests real-time infrastructure telemetry (CPU, RAM, Disk, process health, HTTP status), identifies active system anomalies, and performs vector similarity search against operational runbooks to synthesize structured incident reports.

---

## 🏗️ Architecture

```text
 Telemetry Payload (JSON)
          │
          ▼
   ┌──────────────┐
   │ FastAPI API  │
   └──────┬───────┘
          │
          ▼
   ┌──────────────┐      Anomalies
   │ Rule Engine  ├─────────────────────────┐
   └──────────────┘                         │
                                            ▼
   ┌──────────────┐      Search Query  ┌─────────┐
   │ Chroma Vector├───────────────────►│ RAG     │
   │ Store        │   Runbook Context  │ Synthe- │
   └──────────────┘───────────────────►│ sizer   │
                                       └────┬────┘
                                            │
                                            ▼
                                ┌──────────────────────┐
                                │ Incident Report JSON │
                                └──────────────────────┘
```

---

## ⚡ Key Features

* **Metric & Endpoint Ingestion**: Analyzes system telemetry including CPU, RAM, Disk space, systemd services, and HTTP status codes.
* **Automated Rule Engine**: Flags baseline threshold violations and service failures instantly.
* **Vector Runbook Retrieval**: Uses vector embeddings (`all-MiniLM-L6-v2` via ChromaDB) to pull actionable remediation procedures matching the anomaly signature.
* **Structured Incident Schema**: Emits predictable, strongly typed JSON reports with severity levels, root cause descriptions, action items, and escalation paths.
* **Container-Ready**: Full Docker support with lightweight Python 3.11 image and automated testing via `pytest`.

---

## 🛠️ Tech Stack

* **Language**: Python 3.11
* **API Framework**: FastAPI, Pydantic v2
* **Vector DB & RAG**: ChromaDB, LangChain, HuggingFace Transformers
* **Testing & Quality**: Pytest, HTTPX
* **Containerization**: Docker, Docker Compose

---

## 📁 Repository Structure

```text
ai-it-ops-assistant/
├── app/
│   ├── api/          # Route handlers & endpoints
│   ├── config/       # Environment & metric threshold configuration
│   ├── engine/       # Anomaly & rule evaluation engine
│   ├── models/       # Pydantic data schemas
│   ├── rag/          # Vector database & runbook search
│   ├── services/     # Incident report synthesizer
│   └── main.py       # Application entry point
├── data/
│   ├── runbooks/     # Operational Markdown runbooks
│   └── telemetry_samples/
├── tests/            # Automated test suite
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

* Python 3.11+
* Docker Desktop (optional, for containerization)

### Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/ai-it-ops-assistant.git
   cd ai-it-ops-assistant
   ```

2. **Create a virtual environment and install dependencies:**
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Linux/macOS:
   source .venv/bin/activate

   pip install -r requirements.txt
   ```

3. **Run the API server:**
   ```bash
   python -m app.main
   ```
   The interactive API docs will be available at `http://127.0.0.1:8000/docs`.

### Running with Docker

```bash
docker compose up --build
```

---

## 🧪 Testing

Run the test suite using `pytest`:

```bash
pytest -v
```

---

## 📊 Sample Payload & Output

**POST `/api/v1/telemetry/analyze`**

**Request:**
```json
{
  "cpu_percent": 94.0,
  "ram_percent": 91.0,
  "disk_percent": 97.0,
  "services": { "apache2": "DOWN" },
  "http_endpoints": { "https://app.internal/health": 503 }
}
```

**Response:**
```json
{
  "incident_title": "Incident: Infrastructure Degradation (High CPU utilization: 94.0%, High RAM utilization: 91.0%)",
  "severity": "CRITICAL",
  "likely_cause": "Detected 5 system anomaly/anomalies: High CPU utilization: 94.0%; High RAM utilization: 91.0%; Critical Disk utilization: 97.0%; Service outage: apache2 is DOWN; Endpoint failure: https://app.internal/health returned HTTP 503.",
  "recommended_actions": [
    "Inspect system and application logs under /var/log for critical errors.",
    "Verify process states and resource consumption using system diagnostic tools.",
    "Identify and remove/rotate large log files to free up disk capacity.",
    "Attempt service restart for: apache2"
  ],
  "escalation_required": true,
  "escalation_criteria": "Escalate to On-Call Infrastructure Team if service recovery fails after automated actions or disk usage remains >95%.",
  "sources_consulted": [
    {
      "title": "disk_and_webserver.md",
      "file_path": "data/runbooks/disk_and_webserver.md",
      "relevance_score": 0.58
    }
  ]
}
```
