import json
import redis
from app.config.settings import settings

_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)


def ping() -> bool:
    try:
        return bool(_client.ping())
    except redis.RedisError:
        return False


def get_json(key: str):
    try:
        value = _client.get(key)
        return json.loads(value) if value else None
    except (redis.RedisError, json.JSONDecodeError):
        return None


def set_json(key: str, value, ttl_seconds: int = 300):
    try:
        _client.set(key, json.dumps(value), ex=ttl_seconds)
        return True
    except redis.RedisError:
        return False


# --- Added for Telemetry Rolling History & Rate Limiting ---


def push_metric_sample(
    service_name: str, metric_key: str, value: float, max_samples: int = 30
) -> bool:
    """Push a metric sample to a rolling list for Z-score anomaly detection."""
    try:
        key = f"telemetry:{service_name}:{metric_key}"
        _client.lpush(key, value)
        _client.ltrim(key, 0, max_samples - 1)
        return True
    except redis.RedisError:
        return False


def get_metric_history(service_name: str, metric_key: str) -> list[float]:
    """Retrieve rolling history for dynamic statistical baseline."""
    try:
        key = f"telemetry:{service_name}:{metric_key}"
        raw_values = _client.lrange(key, 0, -1)
        return [float(v) for v in raw_values] if raw_values else []
    except (redis.RedisError, ValueError):
        return []


def is_rate_limited(client_ip: str, limit: int = 60, window_seconds: int = 60) -> bool:
    """Check and update request counts for endpoint rate limiting."""
    try:
        key = f"rate_limit:{client_ip}"
        count = _client.incr(key)
        if count == 1:
            _client.expire(key, window_seconds)
        return count > limit
    except redis.RedisError:
        return False
