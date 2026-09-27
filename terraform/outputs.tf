output "postgres_container_name" {
  description = "Name of the PostgreSQL container"
  value       = docker_container.postgres.name
}

output "redis_container_name" {
  description = "Name of the Redis container"
  value       = docker_container.redis.name
}

output "prometheus_url" {
  description = "Prometheus URL"
  value       = "http://localhost:9090"
}

output "grafana_url" {
  description = "Grafana URL"
  value       = "http://localhost:3000"
}
