# Real-Time Data Engineering Pipeline

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-green.svg)](https://fastapi.tiangolo.com/)
[![Pandas](https://img.shields.io/badge/pandas-2.0+-orange.svg)](https://pandas.pydata.org/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0+-red.svg)](https://www.sqlalchemy.org/)
[![pytest](https://img.shields.io/badge/pytest-7.0+-yellow.svg)](https://docs.pytest.org/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](http://makeapullrequest.com)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [Key Features](#key-features)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [Configuration](#configuration)
- [API Reference](#api-reference)
  - [Trigger ETL Pipeline](#post-apiv1trigger-etl)
  - [Retrieve Metrics](#get-apiv1metrics)
- [Testing](#testing)
- [Monitoring & Logging](#monitoring--logging)
- [Deployment](#deployment)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

---

## 📖 Overview

A **production-grade data engineering pipeline** that ingests live public data, performs automated cleaning and validation, transforms datasets into business insights, persists aggregated metrics into a relational database, and exposes analytical endpoints via a RESTful API.

This project demonstrates end-to-end data engineering best practices, including:

- **ETL Automation**: Scheduled and on-demand data processing with idempotency guarantees.
- **Data Quality**: Schema validation, anomaly detection, and cleansing using Pandas and Pydantic.
- **Analytics**: Aggregated metrics and business intelligence ready for consumption.
- **Observability**: Comprehensive logging, error handling, and health checks.

The pipeline fetches sample user data from the [JSONPlaceholder](https://jsonplaceholder.typicode.com/) API, extracts email domains, counts unique domains, and stores the aggregated metrics in a local SQLite database (or a PostgreSQL instance). The resulting data can be queried via a clean REST API.

---

## 🎯 Use Cases

- **Data Ingestion Prototype**: Quickly set up a data ingestion framework for evaluating external data sources.
- **Analytics Dashboard Backend**: Feed aggregated metrics to a dashboard or BI tool.
- **Learning Tool**: Understand ETL patterns, data validation, and REST API design in Python.
- **Foundation for Real‑Time Pipelines**: Extend to streaming data with Apache Kafka or similar.

---

## 🏗️ Architecture

```mermaid
flowchart LR
    A[Public API\nJSONPlaceholder] --> B[Python Ingestion Module]
    B --> C[Pandas Validation &\nTransformation]
    C --> D[SQLAlchemy ORM]
    D --> E[Relational Database\nSQLite / PostgreSQL]
    E --> F[FastAPI REST\nAnalytics Endpoints]
    
    style A fill:#4CAF50,color:#fff
    style B fill:#2196F3,color:#fff
    style C fill:#FF9800,color:#fff
    style D fill:#9C27B0,color:#fff
    style E fill:#F44336,color:#fff
    style F fill:#00BCD4,color:#fff
```

### Data Flow

| Stage | Component | Description |
|-------|-----------|-------------|
| **Ingestion** | Python Module | Fetches real-time data from external REST API with retries and timeout handling. |
| **Validation** | Pandas + Pydantic | Enforces schema integrity (required fields, data types) and quality rules (non‑null, valid email format). |
| **Transformation** | Pandas | Cleans anomalies (e.g., duplicates), parses email domains, computes aggregates (unique domains, record counts). |
| **Storage** | SQLAlchemy ORM | Manages relational storage with automatic session handling and transaction management. |
| **Exposure** | FastAPI | Serves analytical insights via REST endpoints with pagination and filtering. |

---

## ✨ Key Features

- **🔄 Automated ETL Pipeline**
  - Real‑time external data fetching with configurable timeouts.
  - Anomaly detection (e.g., duplicate records, malformed emails) and data cleansing.
  - Business insight extraction — email domain parsing, count aggregation, and timestamp tracking.
  - Structured metric persistence with automatic schema creation.

- **✅ Data Validation**
  - Pandas transformation pipelines with custom validation functions.
  - Pydantic models for request/response validation and internal data contracts.
  - Integrity checks: non‑null constraints, unique identifiers, and data type enforcement.

- **💾 Relational Storage**
  - SQLAlchemy ORM with support for SQLite (development) and PostgreSQL (production).
  - Automatic session handling and connection pooling.
  - Migration support using Alembic (optional but ready).

- **🌐 RESTful API**
  - FastAPI backend with interactive Swagger UI (`/docs`) and ReDoc (`/redoc`).
  - JSON response formatting with structured error payloads.
  - Comprehensive error handling with meaningful HTTP status codes.

- **🧪 Automated Testing**
  - Full integration test coverage using `pytest`.
  - Endpoint validation and ETL pipeline testing with fixtures.
  - CI/CD ready with GitHub Actions workflow included.

---

## 🛠️ Technology Stack

| Category | Technology | Version |
|----------|------------|---------|
| **Language** | Python | 3.8+ |
| **Web Framework** | FastAPI | 0.95+ |
| **Data Processing** | Pandas | 2.0+ |
| **ORM** | SQLAlchemy | 2.0+ |
| **Database** | SQLite / PostgreSQL | - |
| **Validation** | Pydantic | 2.0+ |
| **Testing** | Pytest | 7.0+ |
| **ASGI Server** | Uvicorn | 0.20+ |
| **Code Quality** | Black, isort, Flake8 | - |

---

## 📁 Project Structure

```plaintext
real-time-pipeline/
│
├── app/
│   ├── __init__.py
│   ├── main.py                # FastAPI application entry point
│   ├── config.py              # Configuration settings (pydantic-settings)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   └── endpoints.py       # REST API route definitions
│   │
│   ├── etl/
│   │   ├── __init__.py
│   │   └── pipeline.py        # ETL logic: ingestion, validation, transformation, load
│   │
│   └── models/
│       ├── __init__.py
│       └── database.py        # SQLAlchemy models & session management
│
├── data/
│   └── pipeline.db            # SQLite database file (created at runtime)
│
├── tests/
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   └── test_pipeline.py       # ETL pipeline integration tests
│
├── .env.example               # Environment variables template
├── .gitignore
├── requirements.txt
├── requirements-dev.txt       # Dev dependencies (testing, linting)
├── pyproject.toml             # Black/isort configuration
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- **Python** 3.8 or higher
- **pip** (Python package manager)
- **Git** (for cloning)
- (Optional) **PostgreSQL** for production use

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/Baqir110/real-time-pipeline.git
   cd real-time-pipeline
   ```

2. **Create and activate a virtual environment**

   ```bash
   python -m venv venv
   ```

   **Windows (PowerShell):**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

   **macOS / Linux:**
   ```bash
   source venv/bin/activate
   ```

3. **Install dependencies**

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

   (Optional) Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure environment** (optional)

   Copy `.env.example` to `.env` and adjust settings such as `DATABASE_URL` or `API_TIMEOUT`.

### Running the Application

1. **Run tests** (optional but recommended)

   ```bash
   python -m pytest -v
   ```

2. **Start the application server**

   ```bash
   python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

3. **Access the API**

   - **Swagger UI**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ReDoc**: [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## ⚙️ Configuration

The application uses environment variables (loaded from `.env` if present) for configuration. Key variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | Connection string for SQLAlchemy | `sqlite:///./data/pipeline.db` |
| `API_BASE_URL` | External data source URL | `https://jsonplaceholder.typicode.com/users` |
| `REQUEST_TIMEOUT` | HTTP request timeout (seconds) | `10` |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | `INFO` |
| `ETL_BATCH_SIZE` | Number of records processed per batch | `100` |

For production use, set `DATABASE_URL` to a PostgreSQL instance (e.g., `postgresql://user:pass@localhost/dbname`).

---

## 📚 API Reference

### `POST /api/v1/trigger-etl`

**Description**: Triggers the live ETL cycle — fetches external data, performs validation and transformation, and persists aggregated metrics to the database.

**Endpoint**: `POST /api/v1/trigger-etl`

**Request Body**: None

**Success Response (200)**:
```json
{
  "status": "success",
  "timestamp": "2026-08-16T21:57:48.123456",
  "records_processed": 10,
  "unique_domains": 8,
  "message": "ETL pipeline executed successfully"
}
```

**Error Response (500)**:
```json
{
  "status": "error",
  "timestamp": "2026-08-16T21:57:48.123456",
  "message": "Failed to fetch external data: Connection timeout"
}
```

---

### `GET /api/v1/metrics`

**Description**: Retrieves all aggregated analytical metrics stored in the pipeline database.

**Endpoint**: `GET /api/v1/metrics`

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | integer | No | Maximum number of records to return (default: 100, max: 1000) |
| `status` | string | No | Filter by status (e.g., `SUCCESS`, `FAILED`) |
| `from_date` | datetime | No | ISO-8601 timestamp (e.g., `2026-08-01T00:00:00`) |
| `to_date` | datetime | No | ISO-8601 timestamp |

**Success Response (200)**:
```json
{
  "status": "success",
  "count": 2,
  "limit": 100,
  "data": [
    {
      "id": 1,
      "metric_name": "total_records_ingested",
      "value": 10.0,
      "status": "SUCCESS",
      "timestamp": "2026-08-16T21:57:48.123456"
    },
    {
      "id": 2,
      "metric_name": "unique_domains_extracted",
      "value": 8.0,
      "status": "SUCCESS",
      "timestamp": "2026-08-16T21:57:48.123456"
    }
  ]
}
```

---

## 🧪 Testing

The project includes comprehensive test coverage using `pytest` and `pytest-cov`.

```bash
# Run all tests with verbose output
python -m pytest -v

# Run specific test file
python -m pytest tests/test_api.py -v

# Run tests with coverage report
python -m pytest --cov=app --cov-report=html

# Run linting (if configured)
black --check app/ tests/
isort --check-only app/ tests/
flake8 app/ tests/
```

---

## 📊 Monitoring & Logging

- **Logging**: Structured logging using Python's `logging` module with configurable levels. Logs include timestamps, module names, and contextual data.
- **Health Check**: A `/health` endpoint is available to verify API and database connectivity.
- **Metrics**: The API exposes Prometheus-compatible metrics via the `/metrics` endpoint (if you enable `prometheus-client`).

---

## 🚢 Deployment

### Docker

A `Dockerfile` and `docker-compose.yml` are provided for containerized deployment.

```bash
# Build and run with Docker Compose
docker-compose up --build
```

### Kubernetes (example)

A sample Kubernetes deployment manifest is available in the `deploy/` directory.

### Production Considerations

- Use PostgreSQL with connection pooling.
- Set `LOG_LEVEL=WARNING` in production.
- Enable HTTPS via a reverse proxy (e.g., Nginx).
- Use environment variables to manage secrets (database credentials).

---

## 🗺️ Roadmap

- [ ] Add Alembic for database migrations.
- [ ] Integrate a scheduler (APScheduler) for periodic ETL runs.
- [ ] Add support for multiple data sources (CSV, Parquet, S3).
- [ ] Implement caching (Redis) for frequently accessed metrics.
- [ ] Add data quality alerts and notifications.
- [ ] Build a simple dashboard (e.g., with Streamlit) to visualize metrics.

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

### Development Guidelines

- Follow **PEP 8** style guidelines.
- Write **docstrings** for all functions and classes.
- Add **unit tests** for new functionality.
- Ensure all tests and linting pass before submitting a PR.

---


## 📧 Contact

**Author**: Muhammad Baqir  
**GitHub**: [github.com/Baqir110](https://github.com/Baqir110)  
**LinkedIn**: [Muhammad Baqir](https://linkedin.com/in/muhammad-baqir-it)

---

<p align="center">
  Made with ❤️ and 🐍 Python
</p>

<p align="center">
  ⭐ Star this repository if you find it useful!
</p>
