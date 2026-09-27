variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "development"
}

variable "enable_monitoring" {
  description = "Enable Prometheus and Grafana"
  type        = bool
  default     = true
}
