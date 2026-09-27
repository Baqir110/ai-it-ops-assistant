# OpsGuard Terraform Infrastructure
# This module provides the foundational infrastructure for OpsGuard.
# Currently supports local development. AWS module can be added cleanly.

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

# ── Local Development Infrastructure ───────────────────────────────────

resource "docker_network" "opsguard" {
  name = "opsguard-network"
}

resource "docker_volume" "postgres_data" {
  name = "opsguard-postgres-data"
}

resource "docker_volume" "redis_data" {
  name = "opsguard-redis-data"
}

resource "docker_volume" "prometheus_data" {
  name = "opsguard-prometheus-data"
}

resource "docker_volume" "grafana_data" {
  name = "opsguard-grafana-data"
}

# PostgreSQL
resource "docker_container" "postgres" {
  name  = "opsguard-postgres"
  image = "postgres:16-alpine"

  env = [
    "POSTGRES_DB=ops",
    "POSTGRES_USER=ops",
    "POSTGRES_PASSWORD=ops",
  ]

  volumes {
    volume_name    = docker_volume.postgres_data.name
    container_path = "/var/lib/postgresql/data"
  }

  networks_advanced {
    name = docker_network.opsguard.name
  }

  healthcheck {
    test     = ["CMD-SHELL", "pg_isready -U ops -d ops"]
    interval = "5s"
    timeout  = "5s"
    retries  = 10
  }

  ports {
    internal = 5432
    external = 5432
  }
}

# Redis
resource "docker_container" "redis" {
  name  = "opsguard-redis"
  image = "redis:7-alpine"

  volumes {
    volume_name    = docker_volume.redis_data.name
    container_path = "/data"
  }

  networks_advanced {
    name = docker_network.opsguard.name
  }

  healthcheck {
    test     = ["CMD", "redis-cli", "ping"]
    interval = "5s"
    timeout  = "5s"
    retries  = 10
  }

  ports {
    internal = 6379
    external = 6379
  }
}

# Prometheus
resource "docker_container" "prometheus" {
  name  = "opsguard-prometheus"
  image = "prom/prometheus:v3.5.0"

  volumes {
    host_path      = "${path.cwd}/prometheus/prometheus.yml"
    container_path = "/etc/prometheus/prometheus.yml"
    read_only      = true
  }

  volumes {
    volume_name    = docker_volume.prometheus_data.name
    container_path = "/prometheus"
  }

  networks_advanced {
    name = docker_network.opsguard.name
  }

  command = [
    "--config.file=/etc/prometheus/prometheus.yml",
    "--storage.tsdb.path=/prometheus",
  ]

  ports {
    internal = 9090
    external = 9090
  }
}

# Grafana
resource "docker_container" "grafana" {
  name  = "opsguard-grafana"
  image = "grafana/grafana:12.1.0"

  env = [
    "GF_SECURITY_ADMIN_USER=admin",
    "GF_SECURITY_ADMIN_PASSWORD=admin",
  ]

  volumes {
    volume_name    = docker_volume.grafana_data.name
    container_path = "/var/lib/grafana"
  }

  networks_advanced {
    name = docker_network.opsguard.name
  }

  ports {
    internal = 3000
    external = 3000
  }

  depends_on = [docker_container.prometheus]
}
